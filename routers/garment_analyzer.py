from fastapi import APIRouter, File, UploadFile, HTTPException
from PIL import Image
from transformers import pipeline
import io
import cv2
import numpy as np
import base64
import requests
import json
from sklearn.cluster import KMeans
from collections import Counter

# Set up the router
router = APIRouter(
    prefix="/garment",
    tags=["Garment Analyzer"]
)

print("Loading Garment Classification Model (CLIP)...")
classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
print("Garment Model loaded successfully!")

# --- 1. THE HIERARCHICAL DICTIONARIES ---
MAIN_CATEGORIES = [
    "traditional indian wear",
    "top wear",
    "bottom wear",
    "dresses and jumpsuits",
    "outerwear and winter wear",
    "footwear"
]

SUB_CATEGORIES = {
    "traditional indian wear": ["saree", "salwar kameez", "anarkali suit", "kurti", "lehenga choli", "sherwani", "dhoti"],
    "top wear": ["t-shirt", "polo shirt", "formal shirt", "casual shirt", "crop top", "peplum top", "tunic"],
    "bottom wear": ["skinny jeans", "straight jeans", "formal trousers", "cargo pants", "palazzo pants", "shorts", "skirt", "joggers"],
    "dresses and jumpsuits": ["maxi dress", "midi dress", "bodycon dress", "wrap dress", "full length jumpsuit", "romper"],
    "outerwear and winter wear": ["blazer", "denim jacket", "leather jacket", "trench coat", "woolen sweater", "hoodie", "cardigan", "coat"],
    "footwear": ["sneakers", "oxford formal shoes", "loafers", "high heels", "flat sandals", "boots", "slippers"]
}

# ⚡ MAPPING TO STRICT FRONTEND CATEGORIES
APP_CATEGORY_MAP = {
    "top wear": "Tops",
    "bottom wear": "Bottoms",
    "footwear": "Footwear",
    "outerwear and winter wear": "Outerwear",
    "dresses and jumpsuits": "Dresses",
    "traditional indian wear": "Dresses" 
}

# --- 2. COLOR EXTRACTION LOGIC ---
def get_dominant_color(cv_image, k=4):
    image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (150, 150), interpolation=cv2.INTER_AREA)
    pixels = image.reshape((image.shape[0] * image.shape[1], 3))
    
    filtered_pixels = [p for p in pixels if not (np.all(p < 30) or np.all(p > 230))]
    if not filtered_pixels:
        filtered_pixels = pixels
        
    filtered_pixels = np.array(filtered_pixels)
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(filtered_pixels)
    
    counts = Counter(kmeans.labels_)
    dominant_cluster_index = counts.most_common(1)[0][0]
    dominant_rgb = [int(x) for x in kmeans.cluster_centers_[dominant_cluster_index]]
    
    hex_color = "#{:02x}{:02x}{:02x}".format(dominant_rgb[0], dominant_rgb[1], dominant_rgb[2])
    return hex_color, dominant_rgb

# --- 3. THE ENDPOINT ---
@router.post("/analyze/")
def analyze_garment(image_file: UploadFile = File(...)):
    try:
        contents = image_file.file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        np_img = np.frombuffer(contents, np.uint8)
        cv_image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        # ---------------------------------------------------------
        # TIER 1: FAST CLIP CLASSIFICATION
        # ---------------------------------------------------------
        main_results = classifier(
            pil_image, 
            candidate_labels=MAIN_CATEGORIES,
            hypothesis_template="a fashion catalog photo showing a {}"
        )
        winning_main_category = main_results[0]["label"]
        main_confidence = round(main_results[0]["score"], 4)

        specific_labels = SUB_CATEGORIES[winning_main_category]
        sub_results = classifier(
            pil_image,
            candidate_labels=specific_labels,
            hypothesis_template="a piece of clothing, specifically a {}, isolated on a background"
        )
        winning_sub_category = sub_results[0]["label"]
        sub_confidence = round(sub_results[0]["score"], 4)

        item_name = winning_sub_category.title()
        base64_image = base64.b64encode(contents).decode('utf-8')

        # ---------------------------------------------------------
        # TIER 2: OLLAMA LOGIC
        # ---------------------------------------------------------
        if main_confidence < 0.70 or sub_confidence < 0.70:
            # SCENARIO A: CLIP is confused. Let Ollama do EVERYTHING.
            print(f"⚠️ CLIP Confidence Low (Main: {main_confidence}, Sub: {sub_confidence}). Ollama doing FULL rescue...")
            try:
                payload = {
                    "model": "llama3.2-vision",
                    "prompt": "You are a fashion stylist. Analyze this clothing image. 1. Generate a catchy, descriptive 'item_name' (e.g., 'Navy Blue Textured Blazer', 'Classic White Formal Shirt'). 2. Select the 'main_category' strictly from this list ONLY: ['traditional indian wear', 'top wear', 'bottom wear', 'dresses and jumpsuits', 'outerwear and winter wear', 'footwear']. 3. Identify the simple 'sub_category' (e.g., blazer, t-shirt, saree, coat). Output strictly valid JSON with keys 'item_name', 'main_category', and 'sub_category'.",
                    "stream": False,
                    "images": [base64_image],
                    "format": "json"
                }
                
                ollama_res = requests.post("http://localhost:11434/api/generate", json=payload)
                
                if ollama_res.status_code == 200:
                    parsed_json = json.loads(ollama_res.json().get("response", "{}"))
                    
                    if "main_category" in parsed_json and "sub_category" in parsed_json:
                        winning_main_category = parsed_json["main_category"].lower()
                        winning_sub_category = parsed_json["sub_category"].lower()
                        item_name = parsed_json.get("item_name", winning_sub_category.title())
                        
                        main_confidence = 0.99 
                        sub_confidence = 0.99
                        print(f"✅ Ollama Full Rescue Success: {item_name} | {winning_main_category} | {winning_sub_category}")
            except Exception as e:
                print(f"❌ Ollama full rescue failed: {e}")

        else:
            # SCENARIO B: CLIP is confident. Just ask Ollama for a cool NAME.
            print(f"✅ CLIP Confident (Main: {main_confidence}, Sub: {sub_confidence}). Asking Ollama just for a catchy name...")
            try:
                payload = {
                    "model": "llama3.2-vision",
                    "prompt": f"You are a fashion stylist. This item is a {winning_sub_category}. Look at the image and generate a catchy, highly descriptive 'item_name' for it (e.g., 'Crimson Red Linen Button-Up', 'Distressed Denim Jacket'). Output strictly valid JSON with a single key 'item_name'.",
                    "stream": False,
                    "images": [base64_image],
                    "format": "json"
                }
                
                ollama_res = requests.post("http://localhost:11434/api/generate", json=payload)
                
                if ollama_res.status_code == 200:
                    parsed_json = json.loads(ollama_res.json().get("response", "{}"))
                    item_name = parsed_json.get("item_name", winning_sub_category.title())
                    print(f"✅ Ollama Name Generation Success: {item_name}")
            except Exception as e:
                print(f"❌ Ollama name generation failed: {e}")

        # ---------------------------------------------------------
        # FINAL STEPS: Color Extraction & Mapping
        # ---------------------------------------------------------
        hex_code, rgb_val = get_dominant_color(cv_image)
        mapped_app_category = APP_CATEGORY_MAP.get(winning_main_category, "Tops")

        return {
            "status": "success",
            "filename": image_file.filename,
            "item_name": item_name,
            "main_category": winning_main_category,
            "app_category": mapped_app_category,
            "main_category_confidence": main_confidence,
            "sub_category": winning_sub_category,
            "sub_category_confidence": sub_confidence,
            "dominant_color_hex": hex_code,
            "dominant_color_rgb": rgb_val
        }
        
    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
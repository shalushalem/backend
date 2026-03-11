# routers/vision.py

import json
import re
import base64
import cv2
import numpy as np
import requests
from fastapi import APIRouter
from pydantic import BaseModel
from sklearn.cluster import KMeans
from collections import Counter
import prompts

router = APIRouter()

class ImageAnalyzeRequest(BaseModel):
    image_base64: str

# --- ULTIMATE COLOR EXTRACTION LOGIC (AGGRESSIVE SHADOW REJECTION) ---
def get_dominant_color(cv_image, k=3):
    try:
        # 1. Convert to RGB
        image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        
        # 2. Crop to the center (ignore 25% of edges to completely avoid background/mannequin bleed)
        h, w, _ = image.shape
        crop_h, crop_w = int(h * 0.25), int(w * 0.25)
        center_image = image[crop_h:h-crop_h, crop_w:w-crop_w]
        
        # 3. Resize for speed
        center_image = cv2.resize(center_image, (100, 100), interpolation=cv2.INTER_AREA)
        
        # 4. Convert to HSV for smart light filtering
        hsv_image = cv2.cvtColor(center_image, cv2.COLOR_RGB2HSV)
        pixels_rgb = center_image.reshape((-1, 3))
        pixels_hsv = hsv_image.reshape((-1, 3))
        
        # 5. Aggressive Filtering: 
        # Saturation > 20 (Ignores grey/white washed-out areas) 
        # Value > 70 (Aggressively ignores dark shadows and fabric folds) 
        # Value < 245 (Ignores pure camera flash/glare)
        mask = (pixels_hsv[:, 1] > 20) & (pixels_hsv[:, 2] > 70) & (pixels_hsv[:, 2] < 245)
        filtered_rgb = pixels_rgb[mask]
        
        # Fallback 1: If it's a naturally dark/grey shirt, lower the threshold
        if len(filtered_rgb) < 100:
            mask = (pixels_hsv[:, 2] > 30) & (pixels_hsv[:, 2] < 250)
            filtered_rgb = pixels_rgb[mask]
            
            # Fallback 2: Absolute safety net (use all pixels)
            if len(filtered_rgb) == 0:
                filtered_rgb = pixels_rgb 
                
        # 6. Run KMeans on the perfectly lit pixels
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(filtered_rgb)
        
        counts = Counter(kmeans.labels_)
        dominant_cluster_index = counts.most_common(1)[0][0]
        dominant_rgb = [int(x) for x in kmeans.cluster_centers_[dominant_cluster_index]]
        
        # Return as uppercase Hex code
        hex_color = "#{:02x}{:02x}{:02x}".format(dominant_rgb[0], dominant_rgb[1], dominant_rgb[2]).upper()
        return hex_color
    except Exception as e:
        print(f"Color Math Error: {e}")
        return "#000000"  # Safe fallback

@router.post("/api/analyze-image")
def analyze_image(request: ImageAnalyzeRequest):
    # 1. Decode base64 to cv2 image for color extraction
    try:
        base64_data = request.image_base64
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
            
        img_data = base64.b64decode(base64_data)
        np_arr = np.frombuffer(img_data, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        # Extract true color mathematically
        extracted_color_hex = get_dominant_color(cv_image)
    except Exception as e:
        print(f"Color Extraction Exception: {str(e)}")
        extracted_color_hex = "#000000"

    # 2. Ask Ollama for the rest (name, category, pattern, occasions)
    payload = {
        "model": "llama3.2-vision", 
        "prompt": prompts.VISION_ANALYZE_PROMPT,
        "images": [request.image_base64],
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=180)
        response.raise_for_status() 
        
        raw_response = response.json().get("response", "{}")
        clean_response = re.sub(r"```json|```", "", raw_response).strip()
        
        final_data = json.loads(clean_response)
        
        # Override any color Ollama might have guessed with our exact CV2 hex
        final_data["color_code"] = extracted_color_hex
        
        return final_data
        
    except Exception as e:
        print(f"Image Analyze Error: {str(e)}")
        return {
            "name": "New Garment", 
            "category": "Tops", 
            "sub_category": "Unknown",
            "occasions": ["casual"],
            "color_code": extracted_color_hex, 
            "pattern": "plain"
        }
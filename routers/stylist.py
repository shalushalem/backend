import json
import re
import requests
from fastapi import APIRouter
from pydantic import BaseModel

# THIS LINE IS CRITICAL - It defines the 'router' that main.py is looking for
router = APIRouter()

class ImageAnalyzeRequest(BaseModel):
    image_base64: str

URL_GENERATE = "http://localhost:11434/api/generate"

@router.post("/api/analyze-image")
def analyze_image(request: ImageAnalyzeRequest):
    strict_prompt = (
        "Analyze this clothing item and return a JSON object with keys: 'name', 'category', and 'tags' (as an array of strings). "
        "CRITICAL: The 'category' field MUST be exactly one of the following options: ['Tops', 'Bottoms', 'Footwear', 'Outerwear', 'Accessories', 'Dresses']. "
        "Rule: Blazers, jackets, coats, and sweaters must be classified as 'Outerwear', NOT 'Tops'."
    )
    
    payload = {
        "model": "llama3.2-vision", 
        "prompt": strict_prompt,
        "images": [request.image_base64],
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(URL_GENERATE, json=payload, timeout=180)
        response.raise_for_status() 
        raw_response = response.json().get("response", "{}")
        
        # Safe JSON extraction regex
        clean_response = re.sub(r'
http://googleusercontent.com/immersive_entry_chip/0

**To be crystal clear:** I gave you the big file earlier because that's what you pasted to me. If your setup is already split up, use the two blocks above! Let me know if that clears up the `AttributeError` crash you were getting.
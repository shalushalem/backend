import json
import re
import requests
from fastapi import APIRouter
from pydantic import BaseModel
import prompts

router = APIRouter()

class ImageAnalyzeRequest(BaseModel):
    image_base64: str

@router.post("/api/analyze-image")
def analyze_image(request: ImageAnalyzeRequest):
    payload = {
        "model": "llama3.2-vision", 
        "prompt": prompts.VISION_ANALYZE_PROMPT,
        "images": [request.image_base64],
        "stream": False,
        "format": "json"
    }
    try:
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=180)
        
        # Check if the request to Ollama was successful
        response.raise_for_status() 
        
        raw_response = response.json().get("response", "{}")
        
        # FIXED: Removed the stray URL and correctly formed the regex.
        # This removes markdown code block formatting if the model outputs it.
        clean_response = re.sub(r"```json|```", "", raw_response).strip()
        
        return json.loads(clean_response)
        
    except Exception as e:
        print(f"Image Analyze Error: {str(e)}")
        # Returns a safe default if parsing or the network request fails
        return {"name": "New Item", "category": "Tops", "tags": []}
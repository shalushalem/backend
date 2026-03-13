import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from services import llm_service

router = APIRouter()

class PackingRequest(BaseModel):
    destination: str
    duration_days: int
    weather: str = "unknown"
    events: str = "casual sightseeing"
    wardrobe: List[Dict[str, Any]] = []

@router.post("/api/generate-packing")
def generate_packing_list(request: PackingRequest):
    system_instruction = (
        "You are Ahvi's Packing Engine. Your job is to create a packing list for the user's trip.\n"
        "You have been provided with the user's virtual wardrobe (JSON format).\n"
        "CRITICAL RULES:\n"
        "1. Select appropriate items FROM THEIR WARDROBE based on the destination, duration, weather, and events.\n"
        "2. Return ONLY a valid JSON object with the exact keys below. Do not use markdown.\n"
        "{\n"
        "  \"reasoning\": \"A short, 1-sentence explanation of your packing strategy.\",\n"
        "  \"pack_list_ids\": [\"id1\", \"id2\", \"id3\"], (Must be actual $id or id values from the wardrobe data)\n"
        "  \"generic_items\": [\"3 pairs of socks\", \"Toothbrush\", \"Underwear\"] (Things not in the virtual wardrobe)\n"
        "}"
    )
    
    user_prompt = (
        f"Destination: {request.destination}\n"
        f"Days: {request.duration_days}\n"
        f"Weather/Vibe: {request.events} (Weather info: {request.weather})\n"
        f"Wardrobe Data: {json.dumps(request.wardrobe)}"
    )
    
    try:
        messages = [{"role": "user", "content": user_prompt}]
        response_text = llm_service.chat_completion(messages, system_instruction, model="llama3.1", response_format="json")
        
        clean_response = re.sub(r'```json|```', '', response_text).strip()
        return json.loads(clean_response)
        
    except Exception as e:
        print(f"Packing Engine Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not generate packing list.")
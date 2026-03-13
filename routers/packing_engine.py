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
        "1. WARDROBE MATH (DO NOT UNDERPACK!):\n"
        "   - Tops: Pack exactly 1 top FOR EVERY SINGLE DAY of the trip (e.g., 3 days = 3 tops).\n"
        "   - Bottoms: Pack 1 bottom for every 2 days (e.g., 3 days = 2 bottoms).\n"
        "   - Dresses/One-pieces: Pack 1 or 2 depending on the vibe.\n"
        "   - Shoes: 1 comfy pair, 1 dressy pair.\n"
        "   - Outerwear: 1 jacket/sweater if the weather demands it.\n"
        "   Never pack just one outfit for a multi-day trip!\n"
        "2. CLIMATE CONTROL: Look closely at the Weather info. If it's cold, prioritize sweaters/jackets. If it's raining, prioritize closed shoes/jackets. If it's hot, prioritize shorts, camisoles, and sandals.\n"
        "3. Select the absolute ESSENTIAL items FROM THEIR WARDROBE to match your math and the weather.\n"
        "4. Return ONLY a valid JSON object with the exact keys below. Do not use markdown.\n"
        "{\n"
        "  \"suggested_counts\": \"E.g., 'For a 3-day trip, you should pack 3 tops, 2 bottoms, 1 dress, and 2 pairs of shoes.'\",\n"
        "  \"reasoning\": \"A short, 1-sentence explanation of the style strategy for these items based on the weather and destination.\",\n"
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
import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import llm_service

router = APIRouter(prefix="/packing", tags=["Packing Engine"])

class PackingRequest(BaseModel):
    destination: str
    duration_days: int
    weather: str
    events: str = "casual sightseeing"

@router.post("/generate")
def generate_packing_list(request: PackingRequest):
    system_instruction = (
        "You are Ahvi's Packing Engine. Generate a highly practical, minimalist "
        "packing list based on the user's trip details. "
        "Return ONLY a JSON object with categories as keys and arrays of strings as values. "
        "Example: {'tops': ['3 casual t-shirts', '1 formal shirt'], 'bottoms': ['2 jeans']}"
    )
    
    user_prompt = (
        f"Destination: {request.destination}\n"
        f"Days: {request.duration_days}\n"
        f"Weather: {request.weather}\n"
        f"Planned Events: {request.events}"
    )
    
    try:
        messages = [{"role": "user", "content": user_prompt}]
        # Using mistral or llama3.1 for logical reasoning
        response_text = llm_service.chat_completion(messages, system_instruction, model="llama3.1")
        
        clean_response = re.sub(r'```json|```', '', response_text).strip()
        return json.loads(clean_response)
        
    except Exception as e:
        print(f"Packing Engine Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not generate packing list.")
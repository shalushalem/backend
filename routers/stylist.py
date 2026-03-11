import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services import llm_service

router = APIRouter()

# Notice we no longer accept base64 images here. We accept the CLIP output.
class ItemContextRequest(BaseModel):
    main_category: str
    sub_category: str
    color_hex: str

@router.post("/api/item-suggestions")
def get_item_suggestions(request: ItemContextRequest):
    system_instruction = (
        "You are Ahvi's Fashion Knowledge Engine. The user just uploaded a new garment. "
        "Based on the provided attributes, return a JSON object with: "
        "1. 'name' (A catchy, descriptive name for the item) "
        "2. 'tags' (array of 4 style keywords like 'streetwear', 'vintage') "
        "3. 'pairing_rules' (array of 2 short rules on what to wear this with). "
        "Output ONLY raw JSON."
    )
    
    user_prompt = (
        f"Item: {request.sub_category}\n"
        f"Category: {request.main_category}\n"
        f"Color Hex: {request.color_hex}"
    )
    
    try:
        messages = [{"role": "user", "content": user_prompt}]
        # Using the much faster, cheaper text model
        response_text = llm_service.chat_completion(messages, system_instruction, model="llama3.1")
        
        # Safe JSON extraction
        clean_response = re.sub(r'```json|```', '', response_text).strip()
        return json.loads(clean_response)
        
    except Exception as e:
        print(f"Stylist Text Engine Error: {str(e)}")
        # Safe fallback
        return {
            "name": f"{request.sub_category.title()}",
            "tags": ["versatile", "casual"],
            "pairing_rules": ["Pair with neutral basics.", "Layer depending on weather."]
        }
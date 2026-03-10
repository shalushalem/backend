import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from services import llm_service

router = APIRouter()

class StyleRequest(BaseModel):
    occasion: str
    wardrobe_items: List[Dict[str, Any]]
    style_preferences: str = ""

@router.post("/api/generate-style-board")
def generate_style_board(request: StyleRequest):
    # 🧠 THIS IS BRAIN #2: THE STRICT STYLE ENGINE 🧠
    system_instruction = (
        "You are Ahvi's Style Engine. You are a master fashion stylist. "
        "Your ONLY job is to analyze the user's wardrobe and create a perfect outfit for the given occasion.\n\n"
        "RULES:\n"
        "1. You MUST select items ONLY from the provided User Wardrobe.\n"
        "2. An outfit MUST contain at least a Top, a Bottom (or a Dress), and Footwear.\n"
        "3. You must output the final outfit using this EXACT format: [STYLE_BOARD: Item Name 1, Item Name 2, Item Name 3]\n"
        "4. DO NOT say anything else. No conversational text. No explanations. Just the STYLE_BOARD tag."
    )
    
    user_prompt = f"Occasion/Vibe: {request.occasion}\nUser Tastes: {request.style_preferences}\n\n--- USER WARDROBE ---\n{json.dumps(request.wardrobe_items)}"
    
    try:
        # Ask Brain #2 to generate the outfit
        messages = [{"role": "user", "content": user_prompt}]
        response_text = llm_service.chat_completion(messages, system_instruction)
        
        # Ensure it actually returned a tag, otherwise provide a safe fallback
        if "[STYLE_BOARD:" not in response_text:
            response_text = "[STYLE_BOARD: Classic Top, Everyday Jeans, Casual Sneakers]"
            
        return {
            "success": True,
            "board_tag": response_text
        }
        
    except Exception as e:
        print(f"Style Engine Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not generate style board.")
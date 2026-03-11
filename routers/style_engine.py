import json
import re
import math
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from services import llm_service

router = APIRouter()

class StyleRequest(BaseModel):
    occasion: str
    wardrobe_items: List[Dict[str, Any]]
    style_preferences: str = ""

# --- 1. THE PYTHON MATH COLOR ENGINE ---
def hex_to_rgb(hex_color: str):
    """Converts a hex string like '#6b7381' to an RGB tuple (107, 115, 129)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return (0, 0, 0) # Safe fallback
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def color_distance(hex1: str, hex2: str):
    """Calculates the Euclidean distance between two hex colors. Lower = better match."""
    if not hex1 or not hex2:
        return 9999 # Return high distance if color is missing
    try:
        r1, g1, b1 = hex_to_rgb(hex1)
        r2, g2, b2 = hex_to_rgb(hex2)
        # Standard Euclidean distance formula for 3D color space
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
    except Exception:
        return 9999

def find_closest_item(target_hex: str, items_list: List[Dict]):
    """Finds the item in the list whose color is mathematically closest to the target_hex."""
    if not items_list:
        return None
    
    best_item = items_list[0]
    best_distance = 9999
    
    for item in items_list:
        item_color = item.get("color", "#000000")
        distance = color_distance(target_hex, item_color)
        
        if distance < best_distance:
            best_distance = distance
            best_item = item
            
    return best_item

# --- 2. THE NEW ENDPOINT ---
@router.post("/api/generate-style-board")
def generate_style_board(request: StyleRequest):
    try:
        # STEP 1: Categorize the Wardrobe 
        tops_and_dresses = [i for i in request.wardrobe_items if i.get("category") in ["Tops", "Dresses"]]
        bottoms = [i for i in request.wardrobe_items if i.get("category") == "Bottoms"]
        shoes = [i for i in request.wardrobe_items if i.get("category") == "Footwear"]

        if not tops_and_dresses:
            raise ValueError("No tops or dresses found in wardrobe.")

        # STEP 2: The Strategist LLM (Creative Brain)
        # Bulletproof Prompt: Force it to act like a data processor, not a conversationalist
        system_instruction = (
            "You are a strict data-processing engine. You do not converse. You do not explain. "
            "Your ONLY job is to output a raw JSON object based on the wardrobe provided.\n"
            "1. Select the absolute best 'Master Piece' (Top or Dress) ID.\n"
            "2. Suggest the ideal complementary HEX color for Bottoms.\n"
            "3. Suggest the ideal HEX color for Footwear.\n\n"
            "CRITICAL: Output ONLY valid JSON. No markdown blocks, no 'Here is your outfit', NO extra text. "
            "Required strictly matching keys: 'master_piece_id', 'target_bottom_hex', 'target_shoe_hex'."
        )
        
        user_prompt = (
            f"Occasion/Vibe: {request.occasion}\n"
            f"User Tastes: {request.style_preferences}\n\n"
            f"--- AVAILABLE TOPS & DRESSES ---\n{json.dumps(tops_and_dresses)}"
        )
        
        messages = [{"role": "user", "content": user_prompt}]
        
        # EXACT FIX: Pass response_format="json" to lock the LLM into JSON generation mode
        response_text = llm_service.chat_completion(
            messages, 
            system_instruction, 
            model="llama3.1",
            response_format="json" 
        )
        
        # Clean and parse the JSON safely
        clean_json = re.sub(r'```json|```', '', response_text).strip()
        strategy = json.loads(clean_json)
        
        # STEP 3: The Python Math Matcher (Instant execution)
        final_outfit_ids = []
        
        # 3A. Add the Master Piece picked by the LLM
        final_outfit_ids.append(strategy.get("master_piece_id"))
        
        # 3B. Instantly find the closest matching bottom using math
        target_bottom_color = strategy.get("target_bottom_hex", "#000000")
        best_bottom = find_closest_item(target_bottom_color, bottoms)
        if best_bottom:
            final_outfit_ids.append(best_bottom.get("$id") or best_bottom.get("id"))
            
        # 3C. Instantly find the closest matching shoes using math
        target_shoe_color = strategy.get("target_shoe_hex", "#000000")
        best_shoe = find_closest_item(target_shoe_color, shoes)
        if best_shoe:
            final_outfit_ids.append(best_shoe.get("$id") or best_shoe.get("id"))

        # Clean up any Nones
        final_outfit_ids = [str(item_id) for item_id in final_outfit_ids if item_id]

        # Return in the exact format your frontend parser expects
        board_tag = f"[STYLE_BOARD: {', '.join(final_outfit_ids)}]"

        return {
            "success": True,
            "board_tag": board_tag,
            "debug_strategy": strategy
        }
        
    except Exception as e:
        print(f"Ahvi Pro Style Engine Error: {str(e)}")
        # Safe fallback so the app never crashes
        fallback_ids = [i.get("$id", i.get("id")) for i in request.wardrobe_items[:3]]
        return {
            "success": False,
            "board_tag": f"[STYLE_BOARD: {', '.join([str(i) for i in fallback_ids if i])}]"
        }
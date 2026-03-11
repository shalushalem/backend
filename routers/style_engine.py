# routers/style_engine.py

import json
import random
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import requests

router = APIRouter()

class StyleRequest(BaseModel):
    occasion: str
    wardrobe: List[Dict[str, Any]]

@router.post("/api/generate-outfit")
def generate_outfit(request: StyleRequest):
    occasion = request.occasion.lower()
    wardrobe = request.wardrobe

    # --- STEP 1: FIND THE MASTERPIECE ---
    # Look for Dresses or Tops that match the occasion
    potential_masterpieces = [
        item for item in wardrobe 
        if item.get("category") in ["Dresses", "Tops"] 
        and occasion in [occ.lower() for occ in item.get("occasions", [])]
    ]

    if not potential_masterpieces:
        # Fallback: Pick any Top or Dress if no occasion matches
        potential_masterpieces = [item for item in wardrobe if item.get("category") in ["Dresses", "Tops"]]
    
    if not potential_masterpieces:
        return {"status": "error", "message": "No tops or dresses found in wardrobe to build an outfit."}

    masterpiece = random.choice(potential_masterpieces)
    is_dress = masterpiece.get("category") == "Dresses"

    # --- STEP 2: GATHER CANDIDATES ---
    available_bottoms = [i for i in wardrobe if i.get("category") == "Bottoms" and i != masterpiece]
    available_shoes = [i for i in wardrobe if i.get("category") == "Footwear" and i != masterpiece]
    available_accessories = [i for i in wardrobe if i.get("category") == "Accessories" and i != masterpiece]

    # --- STEP 3: OLLAMA STYLIST WITH STRICT RULES ---
    system_prompt = (
        "You are an expert fashion stylist. I will give you a 'Masterpiece' garment, and lists of available bottoms, shoes, and accessories.\n"
        "CRITICAL RULES FOR OUTFIT COMPOSITION:\n"
        f"1. Is the Masterpiece a Dress? {str(is_dress).upper()}\n"
        "2. IF IT IS A DRESS: You MUST select EXACTLY ONE shoe and EXACTLY ONE accessory (if available). You MUST NOT select a bottom.\n"
        "3. IF IT IS A TOP: You MUST select EXACTLY ONE bottom, EXACTLY ONE shoe, and EXACTLY ONE accessory (if available).\n"
        "4. Analyze color and pattern to make the best match.\n"
        "5. Output ONLY a raw JSON object with keys: 'selected_bottom_name' (null if dress), 'selected_shoe_name', 'selected_accessory_name', and 'styling_reason'.\n"
        "6. You MUST select exact names from the provided candidate lists."
    )

    user_prompt = json.dumps({
        "masterpiece": masterpiece,
        "candidates": {
            "bottoms": available_bottoms if not is_dress else [],
            "shoes": available_shoes,
            "accessories": available_accessories
        }
    })

    payload = {
        "model": "llama3.1",
        "prompt": f"{system_prompt}\n\nDATA:\n{user_prompt}",
        "stream": False,
        "format": "json"
    }

    try:
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
        response.raise_for_status()
        
        raw_response = response.json().get("response", "{}")
        selections = json.loads(raw_response)

        # --- STEP 4: STRICT RULE ENFORCEMENT (PYTHON) ---
        # 🛡️ If Ollama failed to pick a required item, we FORCE it so the UI rules are met!
        
        # Rule 1: If it's a Top, it MUST have a Bottom.
        if not is_dress and not selections.get("selected_bottom_name") and available_bottoms:
            selections["selected_bottom_name"] = random.choice(available_bottoms)["name"]
            
        # Rule 2: Every outfit MUST have Footwear.
        if not selections.get("selected_shoe_name") and available_shoes:
            selections["selected_shoe_name"] = random.choice(available_shoes)["name"]

        # Rule 3: Add accessory if missing but available (Optional, but highly recommended)
        if not selections.get("selected_accessory_name") and available_accessories:
            selections["selected_accessory_name"] = random.choice(available_accessories)["name"]

        # --- STEP 5: ASSEMBLE OUTFIT ---
        final_outfit = [masterpiece]
        
        for item in available_bottoms + available_shoes + available_accessories:
            if item.get("name") in [
                selections.get("selected_bottom_name"), 
                selections.get("selected_shoe_name"), 
                selections.get("selected_accessory_name")
            ]:
                final_outfit.append(item)

        item_names = [item.get("name") for item in final_outfit]
        style_board_tag = f"[STYLE_BOARD: {', '.join(item_names)}]"

        return {
            "status": "success",
            "masterpiece": masterpiece.get("name"),
            "outfit": final_outfit,
            "styling_reason": selections.get("styling_reason", "A perfectly balanced look based on your wardrobe."),
            "style_board_tag": style_board_tag
        }

    except Exception as e:
        print(f"Style Engine Error: {e}")
        # Absolute Fallback: Still follow the 1 Top + 1 Bottom + 1 Shoe rule!
        fallback_outfit = [masterpiece]
        if available_bottoms and not is_dress: fallback_outfit.append(random.choice(available_bottoms))
        if available_shoes: fallback_outfit.append(random.choice(available_shoes))
        if available_accessories: fallback_outfit.append(random.choice(available_accessories))
        
        item_names = [item.get("name") for item in fallback_outfit]
        return {
            "status": "fallback",
            "outfit": fallback_outfit,
            "style_board_tag": f"[STYLE_BOARD: {', '.join(item_names)}]"
        }
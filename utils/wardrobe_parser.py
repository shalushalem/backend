# utils/wardrobe_parser.py
import re

def extract_and_clean_response(llama_text: str, wardrobe: list) -> dict:
    """
    Parses CHIPS, PACK_LIST, and STYLE_BOARD from the LLM response.
    Ensures valid IDs are used, auto-fills missing categories, and cleans the conversational text.
    """
    response_data = {
        "cleaned_text": llama_text,
        "chips": [],
        "pack_tag": "",
        "board_tag": ""
    }

    # 1. Parse Chips
    chip_match = re.search(r'\[CHIPS?:(.*?)\]', response_data["cleaned_text"], re.IGNORECASE)
    if chip_match:
        response_data["chips"] = [c.strip() for c in chip_match.group(1).split(',') if c.strip()]
    response_data["cleaned_text"] = re.sub(r'\[CHIPS?:.*?\]', '', response_data["cleaned_text"], flags=re.IGNORECASE).strip()

    # 2. Extract Packing List
    pack_match = re.search(r'\[?PACK_LIST:\s*(.*?)(?:\]|\n|$)', response_data["cleaned_text"], re.IGNORECASE)
    if pack_match:
        raw_pack_str = pack_match.group(1).strip()
        valid_pack_ids = []
        selected_pack_strings = [i.strip() for i in raw_pack_str.split(',')]
        for s_str in selected_pack_strings:
            for item in wardrobe:
                # SAFE ID CHECK
                item_id = str(item.get('$id') or item.get('id'))
                if item_id == s_str or item.get('name', '').lower() == s_str.lower():
                    if item_id not in valid_pack_ids:
                        valid_pack_ids.append(item_id)
                    break
        if valid_pack_ids:
            response_data["pack_tag"] = f"[PACK_LIST: {', '.join(valid_pack_ids)}]"
        response_data["cleaned_text"] = re.sub(r'\[?PACK_LIST:.*?(\]|\n|$)', '', response_data["cleaned_text"], flags=re.IGNORECASE).strip()

    # 3. Extract Style Board & Validate Outfit Rules
    board_match = re.search(r'\[?STYLE_BOARD:\s*(.*?)(?:\]|\n|$)', response_data["cleaned_text"], re.IGNORECASE)
    if board_match:
        raw_items_str = board_match.group(1).strip()
        real_ids = []
        selected_strings = [i.strip() for i in raw_items_str.split(',')]
        for s_str in selected_strings:
            for item in wardrobe:
                # SAFE ID CHECK
                item_id = str(item.get('$id') or item.get('id'))
                if item_id == s_str or item.get('name', '').lower() == s_str.lower():
                    if item_id not in real_ids:
                        real_ids.append(item_id)
                    break
        
        selected_items = [item for item in wardrobe if str(item.get('$id') or item.get('id')) in real_ids]
        final_deduplicated_ids = []
        seen_accessory_types = set()
        
        accessory_keywords = ['watch', 'bag', 'belt', 'sunglass', 'ring', 'chain', 'jewelry', 'necklace', 'bracelet', 'accessory', 'earring']
        top_keywords = ['top', 'shirt', 't-shirt', 'blouse', 'sweater', 'hoodie', 'jacket', 'outer'] 
        bottom_keywords = ['bottom', 'pant', 'jeans', 'skirt', 'short', 'trouser', 'cargo']
        footwear_keywords = ['shoe', 'sneaker', 'heel', 'boot', 'sandal', 'footwear', 'flat']
        # NEW: ONE-PIECE KEYWORDS
        one_piece_keywords = ['dress', 'saree', 'gown', 'jumpsuit', 'kurta', 'suit', 'traditional']
        
        has_top = has_bottom = has_footwear = False
        
        for item in selected_items:
            cat = item.get('category', '').lower()
            name = item.get('name', '').lower()
            item_id = str(item.get('$id') or item.get('id'))
            
            is_acc = any(kw in cat or kw in name for kw in accessory_keywords)
            # CHECK FOR FULL BODY OUTFITS
            is_one_piece = any(kw in cat or kw in name for kw in one_piece_keywords) and not is_acc
            
            is_top = any(kw in cat for kw in top_keywords) and not is_acc
            is_bottom = any(kw in cat for kw in bottom_keywords) and not is_acc
            is_footwear = any(kw in cat for kw in footwear_keywords) and not is_acc
            
            # ONE-PIECE LOGIC: Counts as both top and bottom
            if is_one_piece and not has_top:
                has_top = True
                has_bottom = True  # Prevents auto-adding pants!
                final_deduplicated_ids.append(item_id)
            elif is_top and not has_top:
                has_top = True
                final_deduplicated_ids.append(item_id)
            elif is_bottom and not has_bottom:
                has_bottom = True
                final_deduplicated_ids.append(item_id)
            elif is_footwear and not has_footwear:
                has_footwear = True
                final_deduplicated_ids.append(item_id)
            elif is_acc:
                matched_acc_type = next((kw for kw in accessory_keywords if kw in cat or kw in name), None)
                if matched_acc_type and matched_acc_type not in seen_accessory_types:
                    seen_accessory_types.add(matched_acc_type)
                    final_deduplicated_ids.append(item_id)
            else:
                if item_id not in final_deduplicated_ids:
                    final_deduplicated_ids.append(item_id)

        # Auto-fill missing required items
        if not has_top:
            for w in wardrobe:
                w_id = str(w.get('$id') or w.get('id'))
                if w_id not in final_deduplicated_ids and any(kw in w.get('category', '').lower() for kw in top_keywords):
                    final_deduplicated_ids.append(w_id)
                    break
        if not has_bottom:
            for w in wardrobe:
                w_id = str(w.get('$id') or w.get('id'))
                if w_id not in final_deduplicated_ids and any(kw in w.get('category', '').lower() for kw in bottom_keywords):
                    final_deduplicated_ids.append(w_id)
                    break
        if not has_footwear:
            for w in wardrobe:
                w_id = str(w.get('$id') or w.get('id'))
                if w_id not in final_deduplicated_ids and any(kw in w.get('category', '').lower() for kw in footwear_keywords):
                    final_deduplicated_ids.append(w_id)
                    break
        
        # NOTE: Accessory auto-fill is intentionally removed to prevent hallucinated accessories

        if final_deduplicated_ids:
            response_data["board_tag"] = f"[STYLE_BOARD: {', '.join(final_deduplicated_ids)}]"
        response_data["cleaned_text"] = re.sub(r'\[?STYLE_BOARD:.*?(\]|\n|$)', '', response_data["cleaned_text"], flags=re.IGNORECASE).strip()

    # 4. Final Text Cleanup (Removing stray IDs and artifacts)
    for item in wardrobe:
        item_id = str(item.get("$id") or item.get("id", ""))
        if item_id and item_id in response_data["cleaned_text"]:
            response_data["cleaned_text"] = response_data["cleaned_text"].replace(item_id, "")
    
    response_data["cleaned_text"] = re.sub(r'\b(item|items|id1|id2|id3|id4)\b', '', response_data["cleaned_text"], flags=re.IGNORECASE)
    response_data["cleaned_text"] = re.sub(r'\(\s*[,\s]*\)', '', response_data["cleaned_text"]) 
    response_data["cleaned_text"] = re.sub(r'\s{2,}', ' ', response_data["cleaned_text"]).strip() 

    return response_data
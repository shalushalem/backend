# routers/chat.py

import json
import re
import requests
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from deep_translator import GoogleTranslator

from services import translation, llm_service
from utils import wardrobe_parser
import prompts
from worker import run_heavy_audio_task

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class TextChatRequest(BaseModel):
    messages: List[Message]
    language: str 
    current_memory: str
    user_profile: Dict[str, Any] = {} 
    wardrobe_items: List[Dict[str, Any]] = []

@router.post("/api/text")
def text_chat(request: TextChatRequest):
    raw_user_input = request.messages[-1].content
    user_memory = request.current_memory
    wardrobe = request.wardrobe_items 
    
    # 1. Detect & Translate
    has_telugu = bool(re.search(r'[\u0C00-\u0C7F]', raw_user_input))
    has_hindi = bool(re.search(r'[\u0900-\u097F]', raw_user_input))
    target_lang = "en"
    
    if has_telugu:
        input_type, target_lang = "telugu_script", "te"
        try: english_input = GoogleTranslator(source='te', target='en').translate(raw_user_input)
        except: english_input = raw_user_input
    elif has_hindi:
        input_type, target_lang = "hindi_script", "hi"
        try: english_input = GoogleTranslator(source='hi', target='en').translate(raw_user_input)
        except: english_input = raw_user_input
    else:
        input_type = translation.dynamic_nlp_language_detector(raw_user_input)
        if input_type == "tanglish": target_lang, english_input = "te", translation.transliterate_and_translate(raw_user_input, "te")
        elif input_type == "hinglish": target_lang, english_input = "hi", translation.transliterate_and_translate(raw_user_input, "hi")
        else: english_input = raw_user_input 

    # 2. Update Memory
    mem_prompt = prompts.UPDATE_MEMORY_PROMPT.format(new_user_text=english_input, current_memory=user_memory)
    new_memory_res = llm_service.generate_text(mem_prompt, options={"temperature": 0.0})
    new_memory = new_memory_res if new_memory_res and "none" not in new_memory_res.lower() else user_memory

    # 🚀 3. THE SMART INTENT ROUTER 🚀
    print("🧠 Routing to Brain #0 (Intent Analyzer)...")
    
    router_payload = {
        "model": "llama3.1",
        "prompt": f"{prompts.INTENT_ROUTER_PROMPT}\n\nUser Message: '{english_input}'\nWardrobe Size: {len(wardrobe)} items.",
        "stream": False,
        "format": "json"
    }
    
    style_tag = ""
    dynamic_chips = []
    clarifying_msg = ""
    styling_reason = ""
    outfit_names_str = ""
    
    try:
        router_res = requests.post("http://localhost:11434/api/generate", json=router_payload, timeout=30)
        
        raw_router = router_res.json().get("response", "{}")
        clean_router = re.sub(r"```json|```", "", raw_router).strip()
        router_data = json.loads(clean_router)
        
        wants_outfit = router_data.get("wants_outfit", False)
        has_context = router_data.get("has_context", False)
        
        if wants_outfit and not has_context:
            print("🛑 Missing Context! Asking clarifying questions...")
            clarifying_msg = router_data.get("clarifying_question", "Where are we heading? Tell me the vibe!")
            dynamic_chips = router_data.get("chips", ["Casual Hangout", "Night Out", "Office"])
            
        elif wants_outfit and has_context and wardrobe:
            occasion = router_data.get("occasion", english_input)
            print(f"✅ Context clear (Occasion: {occasion}). Triggering Style Engine...")
            
            style_payload = {"occasion": occasion, "wardrobe": wardrobe}
            style_res = requests.post("http://localhost:8000/api/generate-outfit", json=style_payload)
            
            if style_res.status_code == 200:
                style_data = style_res.json()
                style_tag = style_data.get("style_board_tag", "")
                styling_reason = style_data.get("styling_reason", "")
                
                outfit_items = style_data.get("outfit", [])
                outfit_names_list = [item.get("name") for item in outfit_items if item.get("name")]
                outfit_names_str = ", ".join(outfit_names_list)
                
    except Exception as e:
        print(f"Intent Router / Style Engine Error: {e}")

    # 🚀 4. Setup Chat Context (Brain #1) 🚀
    processed_messages = []
    for msg in request.messages[:-1]:
        clean_content = msg.content
        if msg.role == "assistant":
            clean_content = re.sub(r'\[STYLE_BOARD:.*?\]', '', clean_content, flags=re.IGNORECASE)
            clean_content = re.sub(r'\[PACK_LIST:.*?\]', '', clean_content, flags=re.IGNORECASE)
            clean_content = re.sub(r'\[CHIPS:.*?\]', '', clean_content, flags=re.IGNORECASE)
            clean_content = clean_content.strip()
            
        if clean_content:
            processed_messages.append({"role": msg.role, "content": clean_content})

    processed_messages.append({"role": "user", "content": english_input})
    
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        system_instruction = f.read()
    
    system_instruction += (
        "\n\nCRITICAL TONE RULES:\n"
        "1. You are texting a close friend. Keep it SHORT (1-2 sentences maximum). No long paragraphs.\n"
        "2. NEVER use cheesy AI phrases like 'How can I help you?'.\n"
        "3. Use modern, casual slang naturally (e.g., vibes, tbh, slay, lowkey).\n"
    )
    
    system_instruction += f"\nWHAT YOU KNOW ABOUT THEIR TASTE: {new_memory}\n"
    
    if clarifying_msg:
        system_instruction += (
            f"\n\n🚨 URGENT INSTRUCTION 🚨\n"
            f"The user wants an outfit, but we don't know the occasion.\n"
            f"You MUST ask this exact question or something very similar: '{clarifying_msg}'\n"
            f"DO NOT suggest any clothes yet."
        )
    elif style_tag:
        system_instruction += (
            f"\n\n🚨 ANTI-HALLUCINATION PROTOCOL 🚨\n"
            f"The Style Engine has selected THIS EXACT outfit: {outfit_names_str}\n" 
            f"The stylist picked this because: {styling_reason}\n"
            "1. You are FORBIDDEN from mentioning any clothing items that are not in this list.\n"
            "2. Hype up this specific outfit based on their occasion.\n"
            "3. DO NOT output the [STYLE_BOARD] tag yourself."
        )
    elif wardrobe:
        system_instruction += f"\n--- USER'S VIRTUAL WARDROBE ---\n{json.dumps(wardrobe)}\n"

    # 5. Generate Response
    llama_english_response = llm_service.chat_completion(processed_messages, system_instruction)
    
    # 🚨 DESTROY HALLUCINATED TAGS: Forcefully delete any fake Style Board tags the LLM tries to make
    llama_english_response = re.sub(r'\[STYLE_BOARD:.*?\]', '', llama_english_response, flags=re.IGNORECASE).strip()
    
    # Inject valid tags for the UI Parser
    if dynamic_chips:
        chips_str = ", ".join(dynamic_chips)
        llama_english_response += f"\n[CHIPS: {chips_str}]"
        
    parsed_data = wardrobe_parser.extract_and_clean_response(llama_english_response, wardrobe)
    llama_english_response = parsed_data["cleaned_text"]
    chips_list = parsed_data["chips"]
    pack_tag = parsed_data["pack_tag"]

    # 6. Translate Back
    if input_type in ["telugu_script", "hindi_script", "tanglish", "hinglish"]:
        if "script" in input_type:
            final_output = translation.translate_to_script_and_romanized(llama_english_response, target_lang)["native_script"]
        else:
            final_output = translation.generate_natural_romanized(llama_english_response, input_type)
    else:
        final_output = llama_english_response

    # 7. Celery Audio Task
    task = run_heavy_audio_task.delay(final_output, target_lang)

    # 8. EXTRACT IDS FOR THE FRONTEND STYLE BOARD PAGE
    extracted_board_ids = ""
    # 🚨 USE THE TRUE STYLE TAG DIRECTLY FROM THE ENGINE
    if style_tag:
        match = re.search(r'\[STYLE_BOARD:\s*(.*?)\]', style_tag)
        if match:
            extracted_board_ids = match.group(1).strip()

    if pack_tag: final_output = f"{final_output}\n{pack_tag}"

    return {
        "message": {"role": "assistant", "content": final_output},
        "updated_memory": new_memory,
        "images": [], 
        "chips": chips_list,
        "audio_job_id": task.id,
        "board_ids": extracted_board_ids
    }
import json
import re
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

    # 🚀 3. MULTI-BRAIN ORCHESTRATION: Trigger Style Engine if needed 🚀
    is_style_req = any(word in english_input.lower() for word in ["style board", "outfit", "wear", "party", "dress", "look", "saree", "suit", "clothes", "shirt", "pant"])
    
    style_tag = ""
    if is_style_req and wardrobe:
        print("🧠 Routing to Brain #2 (Style Engine)...")
        # 💥 NEW AGGRESSIVE PROMPT FOR BRAIN 2 💥
        style_sys_prompt = (
            "You are a strict fashion stylist AI. Your ONLY job is to select a complete outfit from the provided JSON wardrobe.\n"
            "CRITICAL RULES:\n"
            "1. You MUST select at least 3 items: A Top (or dress/suit/saree), a Bottom, and Footwear. This is NON-NEGOTIABLE.\n"
            "2. If the user asks for a specific item (like a saree) and they do NOT own it, IGNORE their request and build a full alternative outfit using ONLY the items they actually have.\n"
            "3. Output ONLY a single tag in this exact format: [STYLE_BOARD: Exact Item Name 1, Exact Item Name 2, Exact Item Name 3]\n"
            "4. NEVER output conversational text or explanations."
        )
        user_style_prompt = f"Occasion/Request: {english_input}\nAvailable Wardrobe: {json.dumps(wardrobe)}"
        
        # Ask Brain #2 to pick the clothes
        style_response = llm_service.chat_completion([{"role": "user", "content": user_style_prompt}], style_sys_prompt)
        
        # Extract the tag exactly
        match = re.search(r'\[STYLE_BOARD:.*?\]', style_response)
        if match:
            style_tag = match.group(0)
        else:
            style_tag = ""

    # 4. Setup Chat Context (Brain #1)
    processed_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages[:-1]]
    processed_messages.append({"role": "user", "content": english_input})
    
    with open("system_prompt.txt", "r") as f:
        system_instruction = f.read()
    
    system_instruction += (
        "\n\nCRITICAL TONE RULES:\n"
        "1. You are texting a close friend. Keep it SHORT (1-2 sentences maximum). No long paragraphs.\n"
        "2. NEVER use cheesy AI phrases like 'How can I help you?', 'Let's chat!', or 'Let's get this party started.'\n"
        "3. Use modern, casual slang naturally (e.g., vibes, tbh, slay, lowkey).\n"
    )
    
    system_instruction += f"\nWHAT YOU KNOW ABOUT THEIR TASTE: {new_memory}\n"
    
    # 🚀 💥 ANTI-HALLUCINATION PROTOCOL FOR BRAIN 1 💥 🚀
    if style_tag:
        system_instruction += (
            f"\n\n🚨 ANTI-HALLUCINATION PROTOCOL 🚨\n"
            f"The Style Engine has selected THIS EXACT outfit: {style_tag}\n"
            "1. You are FORBIDDEN from mentioning any clothing items that are not in this list.\n"
            "2. NEVER pretend the user is wearing an item they asked for if it is NOT in the STYLE_BOARD list.\n"
            "3. If the user asked for a specific item (like a 'saree') and it is NOT in the list, you MUST explicitly tell them: 'You don't have a [item] in your wardrobe yet, but I put together this alternative...' and then hype up the outfit that was actually selected.\n"
            "4. DO NOT output the [STYLE_BOARD] tag yourself."
        )
    elif wardrobe:
        system_instruction += f"\n--- USER'S VIRTUAL WARDROBE ---\n{json.dumps(wardrobe)}\n"

    # 5. Generate & Parse Response
    llama_english_response = llm_service.chat_completion(processed_messages, system_instruction)
    
    # 💥 INJECT THE TAG SO THE PARSER CATCHES IT 💥
    if style_tag:
        llama_english_response += f"\n{style_tag}"
        
    parsed_data = wardrobe_parser.extract_and_clean_response(llama_english_response, wardrobe)
    llama_english_response = parsed_data["cleaned_text"]
    chips_list = parsed_data["chips"]
    pack_tag = parsed_data["pack_tag"]
    board_tag = parsed_data["board_tag"]

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

    # 🚀 8. EXTRACT IDS FOR THE FRONTEND STYLE BOARD PAGE 🚀
    extracted_board_ids = ""
    if board_tag:
        match = re.search(r'\[STYLE_BOARD:\s*(.*?)\]', board_tag)
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
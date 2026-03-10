import json
import re
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from deep_translator import GoogleTranslator

from services import translation, llm_service, audio_service
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

    # 3. Setup LLM Chat Context
    processed_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages[:-1]]
    processed_messages.append({"role": "user", "content": english_input})
    
    with open("system_prompt.txt", "r") as f:
        system_instruction = f.read()
    
    # 💥 CRITICAL TONE RULES FOR HUMOR & REALISM 💥
    system_instruction += (
        "\n\nCRITICAL TONE RULES:\n"
        "1. You are texting a close friend. Keep it SHORT (1-2 sentences maximum). No long paragraphs.\n"
        "2. NEVER use cheesy AI phrases like 'How can I help you?', 'Let's chat!', or 'Let's get this party started.'\n"
        "3. Use modern, casual slang naturally (e.g., vibes, tbh, slay, lowkey, outfit crisis).\n"
        "4. If the user just says 'hi' or 'hey', reply with something highly casual and slightly sassy, like 'Hey! What's the outfit crisis today?' or 'Hey bestie, what's the vibe?'\n"
    )
    
    system_instruction += f"\nWHAT YOU KNOW ABOUT THEIR TASTE: {new_memory}\n"
    if wardrobe:
        system_instruction += f"\n--- USER'S VIRTUAL WARDROBE ---\n{json.dumps(wardrobe)}\n"

    # 4. Generate & Parse Response
    llama_english_response = llm_service.chat_completion(processed_messages, system_instruction)
    
    parsed_data = wardrobe_parser.extract_and_clean_response(llama_english_response, wardrobe)
    llama_english_response = parsed_data["cleaned_text"]
    chips_list = parsed_data["chips"]
    pack_tag = parsed_data["pack_tag"]
    board_tag = parsed_data["board_tag"]

    # 5. Translate Back
    if input_type in ["telugu_script", "hindi_script", "tanglish", "hinglish"]:
        if "script" in input_type:
            final_output = translation.translate_to_script_and_romanized(llama_english_response, target_lang)["native_script"]
        else:
            final_output = translation.generate_natural_romanized(llama_english_response, input_type)
    else:
        final_output = llama_english_response

    # 🚀 6. TRUE REDIS QUEUEING (CRASH-PROOF) 🚀
    # This sends the task to Redis and instantly gives us a tracking ID
    task = run_heavy_audio_task.delay(final_output, target_lang)

    if board_tag: final_output = f"{final_output}\n{board_tag}"
    if pack_tag: final_output = f"{final_output}\n{pack_tag}"

    # Return instantly to the user while the worker handles the heavy lifting
    return {
        "message": {"role": "assistant", "content": final_output},
        "updated_memory": new_memory,
        "images": [], 
        "chips": chips_list,
        "audio_job_id": task.id 
    }
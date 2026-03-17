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

# 🚀 OPEN-METEO WEATHER INTEGRATION
def get_weather_forecast(destination: str, days: int) -> str:
    if not destination or destination.lower() == "unknown":
        return "unknown"
    try:
        # 1. Geocode the destination name to get Latitude and Longitude
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={destination}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url, timeout=5)
        geo_data = geo_res.json()
        
        if not geo_data.get("results"):
            return "unknown"
            
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        
        # 2. Fetch the weather (Open-Meteo maxes out at 16 days for free tier)
        forecast_days = min(days, 16)
        if forecast_days < 1: forecast_days = 1
        
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto&forecast_days={forecast_days}"
        weather_res = requests.get(weather_url, timeout=5)
        w_data = weather_res.json()
        
        daily = w_data.get("daily", {})
        if not daily:
            return "unknown"
            
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        
        # Calculate averages for the trip
        avg_max = sum(max_temps) / len(max_temps) if max_temps else 0
        avg_min = sum(min_temps) / len(min_temps) if min_temps else 0
        total_precip = sum(precip) if precip else 0
        
        weather_desc = f"Avg High: {avg_max:.1f}°C, Avg Low: {avg_min:.1f}°C"
        if total_precip > 10:
            weather_desc += f". Expect RAIN ({total_precip:.1f}mm total)."
        else:
            weather_desc += ". Mostly dry."
            
        print(f"🌤️ Weather for {destination}: {weather_desc}")
        return weather_desc
        
    except Exception as e:
        print(f"⚠️ Weather API Error: {e}")
        return "unknown"


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
    
    conversation_context = "\n".join([f"{msg.role.upper()}: {msg.content}" for msg in request.messages[-4:]])
    
    # 🚀 COMBINED RULES: Anti-Looping, Smart Durations, and Weather Verification!
    router_payload = {
        "model": "llama3.1",
        "prompt": f"{prompts.INTENT_ROUTER_PROMPT}\n\n🚨 CRITICAL ROUTER RULES:\n1. INTENT MEMORY: If the user is talking about a vacation/trip/packing in the context, STAY IN PACKING MODE (wants_packing=true, wants_outfit=false). Do not ask about 'style vibe'.\n2. WEATHER COMPATIBILITY: If they want a packing list, the 'destination' MUST be a real geographic city or country. If they give a generic location like 'grandma's house' or 'the beach', set has_packing_context to False and ask 'What city is that in?'.\n3. DESTINATIONS: 'Goa', 'Bali', etc. are perfectly valid. Do NOT ask 'What city is that in?' for real places.\n4. DURATION: If they give a valid destination but no duration, silently default to 3 days. Do not ask for the duration.\n\nRecent Conversation Context:\n{conversation_context}\n\nCurrent Target Message: '{english_input}'\nWardrobe Size: {len(wardrobe)} items.",
        "stream": False,
        "format": "json"
    }
    
    style_tag = ""
    dynamic_chips = []
    clarifying_msg = ""
    styling_reason = ""
    outfit_names_str = ""
    pack_tag = ""
    generic_pack_items = []
    packed_names_str = ""
    suggested_counts = ""
    
    try:
        router_res = requests.post("http://localhost:11434/api/generate", json=router_payload, timeout=60)
        
        raw_router = router_res.json().get("response", "{}")
        clean_router = re.sub(r"```json|```", "", raw_router).strip()
        router_data = json.loads(clean_router)
        
        wants_outfit = router_data.get("wants_outfit", False)
        has_context = router_data.get("has_context", False)
        
        wants_packing = router_data.get("wants_packing", False)
        has_packing_context = router_data.get("has_packing_context", False)

        # 🚀 THE SMART FAIL-SAFE: Protects Style Engine vs Packing Engine
        conversation_text = conversation_context.lower() + " " + english_input.lower()
        
        # 1. If they explicitly ask for an outfit/what to wear, PROTECT THE STYLE ENGINE!
        if "outfit" in english_input.lower() or "wear" in english_input.lower() or "style" in english_input.lower():
            wants_outfit = True
            wants_packing = False
            
        # 2. Otherwise, if they mention packing/trips, trigger the Packing Engine
        elif "pack" in conversation_text or "trip" in conversation_text or "vacation" in conversation_text or "suitcase" in conversation_text:
            wants_packing = True
            wants_outfit = False
        
        # --- SCENARIO B: WANTS PACKING LIST (MOVED TO TOP FOR PRIORITY) ---
        if wants_packing and not has_packing_context:
             print("🛑 Missing Trip Details! Asking for destination/days...")
             clarifying_msg = router_data.get("clarifying_question", "Ooh a trip! ✈️ What city are we heading to?")
             dynamic_chips = ["Goa", "Mumbai", "London"]

        elif wants_packing and has_packing_context:
             if not wardrobe:
                 print("🛑 User wants a packing list, but their virtual wardrobe is empty!")
                 clarifying_msg = "I'd love to pack your bags, but your virtual wardrobe is empty! 😭 Upload some clothes first so I know what we're working with."
             else:
                 trip_details = router_data.get("trip_details", {})
                 print(f"✅ Trip Details clear ({trip_details}). Triggering Packing Engine...")
                 
                 # Safely parse duration, default to 3 if missing
                 raw_duration = trip_details.get("duration")
                 if not raw_duration:
                     safe_duration = 3
                 elif isinstance(raw_duration, str):
                     match = re.search(r'\d+', raw_duration)
                     safe_duration = int(match.group()) if match else 3
                 else:
                     try: safe_duration = int(raw_duration)
                     except: safe_duration = 3

                 dest = trip_details.get("destination") or "unknown"
                 
                 # 🚀 FETCH REAL WEATHER 🚀
                 print(f"🌍 Geocoding and fetching weather for {dest}...")
                 real_weather = get_weather_forecast(dest, safe_duration)

                 pack_payload = {
                     "destination": dest,
                     "duration_days": safe_duration,
                     "events": trip_details.get("vibe") or "general travel", 
                     "weather": real_weather, 
                     "wardrobe": wardrobe
                 }
                 
                 print(f"🚀 Sending payload to Packing Engine: {pack_payload}")
                 pack_res = requests.post("http://localhost:8000/api/generate-packing", json=pack_payload)
                 
                 if pack_res.status_code == 200:
                     print("✅ Packing Engine API Success!")
                     pack_data = pack_res.json()
                     styling_reason = pack_data.get("reasoning", "")
                     suggested_counts = pack_data.get("suggested_counts", "") 
                     pack_ids = pack_data.get("pack_list_ids", [])
                     generic_pack_items = pack_data.get("generic_items", [])
                     
                     if pack_ids:
                         pack_tag = f"[PACK_LIST: {', '.join(pack_ids)}]"
                         packed_item_names = []
                         for item in wardrobe:
                             item_id = str(item.get("$id", item.get("id", "")))
                             if item_id in pack_ids:
                                 packed_item_names.append(item.get("name", "A cute item"))
                         packed_names_str = ", ".join(packed_item_names)
                 else:
                     print(f"❌ Packing Engine API Failed! Status: {pack_res.status_code}")
                     print(f"❌ Error Details: {pack_res.text}")

        # --- SCENARIO A: WANTS OUTFIT ---
        elif wants_outfit and not has_context:
            print("🛑 Missing Outfit Context! Asking clarifying questions...")
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
                outfit_names_str = ", ".join([item.get("name") for item in outfit_items if item.get("name")])

    except Exception as e:
        print(f"Intent Router / Engine Error: {e}")

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
        "1. You are texting a close friend. Keep it SHORT.\n"
        "2. NEVER use cheesy AI phrases like 'How can I help you?'.\n"
        "3. Use modern, casual slang naturally (e.g., vibes, tbh, slay, lowkey).\n"
    )
    
    system_instruction += f"\nWHAT YOU KNOW ABOUT THEIR TASTE: {new_memory}\n"
    
    if clarifying_msg:
        system_instruction += (
            f"\n\n🚨 URGENT INSTRUCTION 🚨\n"
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
    elif pack_tag:
        generic_items_str = ", ".join(generic_pack_items)
        system_instruction += (
            f"\n\n🚨 ANTI-HALLUCINATION PROTOCOL (PACKING) 🚨\n"
            f"The Packing Engine has selected THESE SPECIFIC ITEMS from their virtual wardrobe: {packed_names_str}\n"
            f"Packing Math: {suggested_counts}\n"
            f"Reasoning: {styling_reason}\n"
            f"1. You MUST first tell the user the 'Packing Math' (how many tops, bottoms, etc., they need).\n"
            f"2. Mention the specific weather conditions Ahvi noticed.\n"
            f"3. Do not list the specific items in the text. Just say 'I've added the perfect items to your checklist!'\n"
            f"4. Tell them not to forget their basics: {generic_items_str}.\n"
            "5. DO NOT output the [PACK_LIST] tag yourself."
        )
    elif wardrobe:
        system_instruction += f"\n--- USER'S VIRTUAL WARDROBE ---\n{json.dumps(wardrobe)}\n"

    # 5. Generate Response
    llama_english_response = llm_service.chat_completion(processed_messages, system_instruction)
    
    # 🚨 DESTROY HALLUCINATED TAGS
    llama_english_response = re.sub(r'\[STYLE_BOARD:.*?\]', '', llama_english_response, flags=re.IGNORECASE).strip()
    llama_english_response = re.sub(r'\[PACK_LIST:.*?\]', '', llama_english_response, flags=re.IGNORECASE).strip()
    
    if dynamic_chips:
        chips_str = ", ".join(dynamic_chips)
        llama_english_response += f"\n[CHIPS: {chips_str}]"
        
    parsed_data = wardrobe_parser.extract_and_clean_response(llama_english_response, wardrobe)
    llama_english_response = parsed_data["cleaned_text"]
    chips_list = parsed_data["chips"]

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
    if style_tag:
        match = re.search(r'\[STYLE_BOARD:\s*(.*?)\]', style_tag)
        if match:
            extracted_board_ids = match.group(1).strip()

    if pack_tag: 
        final_output = f"{final_output}\n{pack_tag}"
    elif parsed_data["pack_tag"]:
        final_output = f"{final_output}\n{parsed_data['pack_tag']}"

    return {
        "message": {"role": "assistant", "content": final_output},
        "updated_memory": new_memory,
        "images": [], 
        "chips": chips_list,
        "audio_job_id": task.id,
        "board_ids": extracted_board_ids
    }
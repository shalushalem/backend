# backend/routers/chat.py

import json
import re
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from deep_translator import GoogleTranslator

from services import translation, llm_service
from utils import wardrobe_parser
from worker import run_heavy_audio_task

from brain.nlu.intent_router import nlu_router
from brain.engines.style_builder import style_engine
from brain.context.context_engine import context_engine
from brain.personalization.style_dna_engine import style_dna_engine

from prompts.core_prompts import AHVI_SYSTEM_PROMPT
from prompts.personality_prompts import PERSONALITY_LAYER
from prompts.memory_prompts import UPDATE_MEMORY_PROMPT

router = APIRouter()


# =========================
# SAFE REQUEST WRAPPERS
# =========================
def safe_post(url, payload, timeout=15):
    try:
        return requests.post(url, json=payload, timeout=timeout)
    except Exception as e:
        print(f"⚠️ POST failed: {e}")
        return None


def safe_get(url, timeout=5):
    try:
        return requests.get(url, timeout=timeout)
    except Exception as e:
        print(f"⚠️ GET failed: {e}")
        return None


# =========================
# MODELS
# =========================
class Message(BaseModel):
    role: str
    content: str


class TextChatRequest(BaseModel):
    messages: List[Message]
    language: str
    current_memory: str
    user_profile: Dict[str, Any] = {}
    wardrobe_items: List[Dict[str, Any]] = []


# =========================
# MAIN ENDPOINT
# =========================
@router.post("/api/text")
async def text_chat(request: TextChatRequest):

    # =========================
    # VALIDATION
    # =========================
    if len(request.messages) > 20:
        raise HTTPException(status_code=400, detail="Too many messages")

    if len(str(request.wardrobe_items)) > 50000:
        raise HTTPException(status_code=400, detail="Wardrobe too large")

    if not request.messages:
        return {"message": {"role": "assistant", "content": "Say something first 😅"}}

    raw_user_input = request.messages[-1].content
    user_memory = request.current_memory
    wardrobe = request.wardrobe_items
    user_profile = request.user_profile or {}

    # =========================
    # TRANSLATION
    # =========================
    try:
        has_telugu = bool(re.search(r'[\u0C00-\u0C7F]', raw_user_input))
        has_hindi = bool(re.search(r'[\u0900-\u097F]', raw_user_input))

        if has_telugu:
            english_input = GoogleTranslator(source='te', target='en').translate(raw_user_input)
            target_lang = "te"
        elif has_hindi:
            english_input = GoogleTranslator(source='hi', target='en').translate(raw_user_input)
            target_lang = "hi"
        else:
            english_input = raw_user_input
            target_lang = "en"

    except Exception as e:
        print("⚠️ Translation failed:", e)
        english_input = raw_user_input
        target_lang = "en"

    # =========================
    # MEMORY UPDATE
    # =========================
    try:
        mem_prompt = UPDATE_MEMORY_PROMPT.format(
            new_user_text=english_input,
            current_memory=user_memory
        )

        new_memory = llm_service.generate_text(
            mem_prompt,
            options={"temperature": 0.1}
        )

        if not new_memory or "none" in new_memory.lower():
            new_memory = user_memory

    except Exception as e:
        print("⚠️ Memory update failed:", e)
        new_memory = user_memory

    # =========================
    # INTENT DETECTION
    # =========================
    try:
        intent_data = nlu_router.classify_intent(english_input)
    except Exception as e:
        print("⚠️ Intent failed:", e)
        intent_data = {"intent": "unknown", "slots": {}}

    intent = intent_data.get("intent", "")
    slots = intent_data.get("slots", {})

    wants_outfit = intent == "styling" or any(
        w in english_input.lower()
        for w in ["wear", "outfit", "dress", "style"]
    )

    # =========================
    # STYLE ENGINE
    # =========================
    style_tag = ""
    outfit_names_str = ""
    chips = []

    if wants_outfit:
        if not wardrobe:
            return {
                "message": {
                    "role": "assistant",
                    "content": "I need your wardrobe first 😅 Upload some outfits and I’ll style you!"
                },
                "updated_memory": new_memory,
                "chips": ["Upload Wardrobe"],
                "audio_job_id": "offline",
                "board_ids": ""
            }

        try:
            context = context_engine.build_context(
                user_id="temp",
                intent_data=intent_data,
                wardrobe=wardrobe,
                user_profile=user_profile,
                history=[],
                vision={}
            )

            context = style_dna_engine.enrich_context(context)
            outfit_data = style_engine.build_outfit(context)

            best = outfit_data.get("outfits", [{}])[0]

            matched_ids = []
            matched_names = []

            for item in wardrobe:
                name = item.get("name", "")
                item_id = str(item.get("$id", item.get("id", "")))

                if name in [
                    best.get("top"),
                    best.get("bottom"),
                    best.get("shoes")
                ]:
                    matched_ids.append(item_id)
                    matched_names.append(name)

            if matched_ids:
                style_tag = f"[STYLE_BOARD: {', '.join(matched_ids)}]"
                outfit_names_str = ", ".join(matched_names)
                chips = ["Try another look", "Change vibe", "Casual", "Party"]

        except Exception as e:
            print("⚠️ Style engine failed:", e)

    # =========================
    # BUILD PROMPT
    # =========================
    system_instruction = f"""
{AHVI_SYSTEM_PROMPT}

{PERSONALITY_LAYER}

--- USER MEMORY ---
{new_memory}

--- USER PROFILE ---
Name: {user_profile.get("name", "User")}
Style: {user_profile.get("style", "")}
Colors: {", ".join(user_profile.get("preferred_colors", []))}

--- INSTRUCTIONS ---
- Be conversational and stylish
- Use memory for personalization
- Do NOT hallucinate clothing items
"""

    if outfit_names_str:
        system_instruction += f"\nOutfit Context: {outfit_names_str}"

    # =========================
    # CHAT HISTORY
    # =========================
    processed_messages = []

    for msg in request.messages[-5:]:
        role = msg.role if msg.role in ["user", "assistant"] else "assistant"
        processed_messages.append({
            "role": role,
            "content": msg.content
        })

    # =========================
    # LLM CALL
    # =========================
    try:
        response = llm_service.chat_completion(
            processed_messages,
            system_instruction
        )
    except Exception as e:
        print("⚠️ LLM failed:", e)
        response = "I'm having trouble right now 😅 Try again!"

    # =========================
    # CLEAN RESPONSE
    # =========================
    clean_response = re.sub(r'\[STYLE_BOARD:.*?\]', '', response).strip()

    # =========================
    # AUDIO TASK
    # =========================
    try:
        task = run_heavy_audio_task.delay(clean_response, target_lang)
        audio_job_id = task.id
    except:
        audio_job_id = "offline"

    # =========================
    # FINAL RESPONSE
    # =========================
    return {
        "message": {"role": "assistant", "content": clean_response},
        "updated_memory": new_memory,
        "chips": chips,
        "audio_job_id": audio_job_id,
        "board_ids": style_tag.replace("[STYLE_BOARD:", "").replace("]", "").strip()
    }
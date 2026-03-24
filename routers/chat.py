# backend/routers/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import re

from deep_translator import GoogleTranslator
from worker import run_heavy_audio_task

# ✅ SINGLE BRAIN
from brain.orchestrator import ahvi_orchestrator

router = APIRouter()

# =========================
# MODELS
# =========================
class Message(BaseModel):
    role: str
    content: str


class TextChatRequest(BaseModel):
    messages: List[Message]
    language: str = "en"
    current_memory: Dict[str, Any] = {}
    user_profile: Dict[str, Any] = {}
    wardrobe_items: List[Dict[str, Any]] = []


# =========================
# MAIN ENDPOINT
# =========================
@router.post("/text")
async def text_chat(request: TextChatRequest):

    # =========================
    # BASIC VALIDATION
    # =========================
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    user_input = request.messages[-1].content.strip()

    if not user_input:
        raise HTTPException(status_code=400, detail="Empty message")

    # =========================
    # TRANSLATION (OPTIONAL)
    # =========================
    try:
        has_telugu = bool(re.search(r'[\u0C00-\u0C7F]', user_input))
        has_hindi = bool(re.search(r'[\u0900-\u097F]', user_input))

        if has_telugu:
            english_input = GoogleTranslator(source='te', target='en').translate(user_input)
            target_lang = "te"
        elif has_hindi:
            english_input = GoogleTranslator(source='hi', target='en').translate(user_input)
            target_lang = "hi"
        else:
            english_input = user_input
            target_lang = "en"

    except Exception:
        english_input = user_input
        target_lang = "en"

    # =========================
    # ORCHESTRATOR (CORE BRAIN)
    # =========================
    try:
        result = ahvi_orchestrator.run(
            text=english_input,
            user_id="user_1",
            context={
                "memory": request.current_memory,
                "user_profile": request.user_profile,
                "wardrobe": request.wardrobe_items
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Orchestrator failed: {str(e)}"
        )

    # =========================
    # AUDIO TASK (OPTIONAL)
    # =========================
    try:
        message_text = result.get("message", "")
        task = run_heavy_audio_task.delay(message_text, target_lang)
        audio_job_id = task.id
    except Exception:
        audio_job_id = "offline"

    # =========================
    # FINAL RESPONSE (STANDARDIZED)
    # =========================
    return {
        "success": True,
        "meta": result.get("meta", {}),
        "message": result.get("message", ""),
        "data": result.get("data", {}),
        "cards": result.get("cards", []),
        "actions": result.get("actions", []),
        "audio_job_id": audio_job_id
    }
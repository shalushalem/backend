# backend/services/translation.py

import re
from deep_translator import GoogleTranslator
from services import llm_service

# 🚀 Self-contained language detection prompt
LANGUAGE_DETECTION_PROMPT = """
Analyze the following text and determine its language or script format.
Reply ONLY with one of these exact words:
- english (if it's standard English)
- tanglish (if it's Tamil words written in English letters, e.g., 'Eppadi irukka')
- hinglish (if it's Hindi words written in English letters, e.g., 'Kaise ho')
- telugu_script (if it contains actual Telugu letters like 'ఎలా ఉన్నారు')
- hindi_script (if it contains actual Hindi letters like 'कैसे हो')

Text to analyze: "{text}"
"""

def dynamic_nlp_language_detector(text: str) -> str:
    """
    Uses the local LLM to quickly classify if the romanized text is 
    English, Tanglish, or Hinglish.
    """
    if not text or len(text.strip()) < 2:
        return "english"
        
    # Quick regex checks for native scripts
    if re.search(r'[\u0C00-\u0C7F]', text):
        return "telugu_script"
    if re.search(r'[\u0900-\u097F]', text):
        return "hindi_script"

    # For romanized text, ask the LLM
    try:
        prompt = LANGUAGE_DETECTION_PROMPT.format(text=text)
        
        # Use low temperature for deterministic classification
        response = llm_service.generate_text(prompt, options={"temperature": 0.0})
        clean_res = response.strip().lower()
        
        if "tanglish" in clean_res:
            return "tanglish"
        elif "hinglish" in clean_res:
            return "hinglish"
        else:
            return "english"
            
    except Exception as e:
        print(f"⚠️ NLP Language Detection Error: {e}")
        return "english"

def transliterate_and_translate(text: str, target_lang_code: str) -> str:
    """
    Handles translation from Romanized regional languages (Tanglish/Hinglish)
    to English by using GoogleTranslator.
    """
    try:
        # Example: 'te' for Telugu (used for Tanglish approximation) or 'hi' for Hindi
        translator = GoogleTranslator(source=target_lang_code, target='en')
        english_text = translator.translate(text)
        return english_text
    except Exception as e:
        print(f"⚠️ Transliteration Error: {e}")
        return text

def translate_to_script_and_romanized(english_text: str, target_lang_code: str) -> dict:
    """
    Translates English back to the native script (e.g., Hindi/Telugu).
    """
    try:
        translator = GoogleTranslator(source='en', target=target_lang_code)
        native_script = translator.translate(english_text)
        
        return {
            "native_script": native_script,
            "romanized": native_script # We return native script as fallback if romanized fails
        }
    except Exception as e:
        print(f"⚠️ Translation Back to Script Error: {e}")
        return {"native_script": english_text, "romanized": english_text}

def generate_natural_romanized(english_text: str, style: str) -> str:
    """
    If the user spoke in Tanglish/Hinglish, we want AHVI to reply in the same vibe.
    """
    if style == "english":
        return english_text
        
    prompt = f"""
    Translate the following English text into natural, conversational {style.capitalize()}.
    Write the response entirely in English characters (Romanized).
    Keep it friendly, short, and use modern slang where appropriate.
    Do not use actual Hindi/Telugu script.
    
    English Text: "{english_text}"
    """
    
    try:
        response = llm_service.generate_text(prompt, options={"temperature": 0.7})
        return response.strip()
    except Exception as e:
        print(f"⚠️ Romanized Generation Error: {e}")
        return english_text
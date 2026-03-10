import re
import string
import unicodedata
import requests
from deep_translator import GoogleTranslator

# Import your newly separated LLM service and prompts
from services.llm_service import generate_text
import prompts

# --- DYNAMIC NLP DICTIONARY ---
NLP_ENGLISH_STOPWORDS = {
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his", "she", "her", "it", "its", "they", "them", "their",
    "what", "which", "who", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "have", "has", "had", "do", "does", "did",
    "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "to", "from", "in", "out", "on", "off",
    "when", "where", "why", "how", "all", "any", "some", "no", "not", "so", "can", "could", "will", "would", "just", "now", "yes", "ok", "okay",
    "hi", "hii", "hello", "hey", "bro", "man", "buddy", "dude", "pls", "plz", "please", "yeah", "yep", "nah", "nope",
    "outfit", "dress", "shirt", "pant", "pants", "jeans", "party", "wedding", "casual", "night", "look", "style", "wear", "suggest", "help", "need", "want", "tell",
    "create", "make", "show", "give", "board", "bord", "pic", "picture", "photo", "image", "combo",
    "pack", "travel", "trip", "vacation", "tour", "holiday"
}

def clean_romanized_text(text: str) -> str:
    clean_text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    clean_text = clean_text.replace('c', 'ch')
    if clean_text:
        clean_text = clean_text[0].upper() + clean_text[1:]
    return clean_text

def dynamic_nlp_language_detector(text: str) -> str:
    words = re.findall(r'\b\w+\b', text.lower())
    foreign_words = [w for w in words if w not in NLP_ENGLISH_STOPWORDS]
    
    if len(foreign_words) == 0: 
        return "english" 
        
    isolated_phrase = " ".join(foreign_words)
    
    # Use the prompt from prompts.py
    prompt = prompts.LANGUAGE_DETECT_PROMPT.format(isolated_phrase=isolated_phrase)
    
    ans = generate_text(prompt, options={"temperature": 0.0}).upper()
    
    if "TANGLISH" in ans or "TELUGU" in ans: 
        return "tanglish"
    if "HINGLISH" in ans or "HINDI" in ans: 
        return "hinglish"
        
    return "english"

def transliterate_and_translate(text: str, lang_code: str) -> str:
    try:
        url = "https://inputtools.google.com/request"
        params = {"text": text, "itc": f"{lang_code}-t-i0-und", "num": 1, "cp": 0, "cs": 1, "ie": "utf-8", "oe": "utf-8", "app": "demopage"}
        data = requests.get(url, params=params, timeout=5).json()
        
        if data[0] == "SUCCESS":
            native_script = " ".join([item[1][0] for item in data[1]])
            return GoogleTranslator(source=lang_code, target='en').translate(native_script)
    except: 
        pass
        
    return text

def translate_to_script_and_romanized(english_text: str, target_lang: str):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "en", "tl": target_lang, "dt": ["t", "rm"], "q": english_text}
    
    try:
        data = requests.get(url, params=params, timeout=10).json()
        native_script = "".join([item[0] for item in data[0] if item[0] and item[1]])
        
        last_item = data[0][-1]
        romanized = last_item[2] if len(last_item) >= 3 and last_item[2] else native_script
        
        return {"native_script": native_script.strip(), "romanized": romanized.strip()}
    except:
        return {"native_script": english_text, "romanized": english_text}

def generate_natural_romanized(english_text: str, lang_type: str) -> str:
    target_lang = "te" if lang_type == "tanglish" else "hi"
    translations = translate_to_script_and_romanized(english_text, target_lang)
    strict_romanized = translations["romanized"]
    
    # Use the prompt from prompts.py
    prompt = prompts.NATURAL_ROMANIZED_PROMPT.format(lang_type=lang_type.upper(), english_text=english_text)
    
    ans = generate_text(prompt, options={"temperature": 0.2})
    
    if ans: 
        return ans
        
    return clean_romanized_text(strict_romanized)
# prompts.py
import os

def get_system_prompt() -> str:
    """Reads the core Ahvi system prompt from the text file."""
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        print("⚠️ Warning: system_prompt.txt not found. Using fallback.")
        return "You are Ahvi, a trendy AI Fashion Assistant. Speak English only."

def get_language_detection_prompt(isolated_phrase: str) -> str:
    return (
        f"Analyze these specific words: '{isolated_phrase}'.\n"
        "Are these words Romanized Telugu, Romanized Hindi, or just English?\n"
        "If the words are Telugu, output TANGLISH.\n"
        "If the words are Hindi, output HINGLISH.\n"
        "OUTPUT EXACTLY ONE WORD ONLY: TANGLISH, HINGLISH, or ENGLISH."
    )

def get_memory_extraction_prompt(new_user_text: str, current_memory: str) -> str:
    return (
        "You are a strict Data Extractor. Your ONLY job is to extract permanent fashion facts, "
        "favorite colors, body types, or style preferences from the user's message.\n"
        f"User's Message: '{new_user_text}'\n"
        f"Current Memory: '{current_memory}'\n\n"
        "RULES:\n"
        "1. If the user mentions a permanent preference, combine it with the Current Memory.\n"
        "2. If the user is just asking a question, output exactly the Current Memory.\n"
        "3. OUTPUT ONLY THE RAW MEMORY TEXT."
    )

def get_romanized_rewrite_prompt(english_text: str, lang_type: str) -> str:
    return (
        f"Rewrite this into natural, casual {lang_type.upper()} (WhatsApp style): '{english_text}'\n"
        "KEEP fashion words in English. No intro, no quotes."
    )

IMAGE_ANALYSIS_PROMPT = (
    "Analyze this clothing item and return a JSON object with keys: 'name', 'category', and 'tags' (as an array of strings). "
    "CRITICAL: The 'category' field MUST be exactly one of the following options: ['Tops', 'Bottoms', 'Footwear', 'Outerwear', 'Accessories', 'Dresses']. "
    "Rule: Blazers, jackets, coats, and sweaters must be classified as 'Outerwear', NOT 'Tops'."
)

def get_outfit_naming_prompt(items_str: str) -> str:
    return f"Give a cool, short, 2-to-3 word aesthetic name for an outfit consisting of: {items_str}. Do not explain. Just output the name."
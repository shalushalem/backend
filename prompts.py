import os

# --- Constants (Used with .format() in your routers) ---

UPDATE_MEMORY_PROMPT = (
    "You are a strict Data Extractor. Your ONLY job is to extract permanent fashion facts, "
    "favorite colors, body types, or style preferences from the user's message.\n"
    "User's Message: '{new_user_text}'\n"
    "Current Memory: '{current_memory}'\n\n"
    "RULES:\n"
    "1. If the user mentions a permanent preference, combine it with the Current Memory.\n"
    "2. If the user is just asking a question, output exactly the Current Memory.\n"
    "3. OUTPUT ONLY THE RAW MEMORY TEXT."
)

IMAGE_ANALYSIS_PROMPT = (
    "Analyze this clothing item and return a JSON object with keys: 'name', 'category', and 'tags' (as an array of strings). "
    "CRITICAL: The 'category' field MUST be exactly one of the following options: ['Tops', 'Bottoms', 'Footwear', 'Outerwear', 'Accessories', 'Dresses']. "
    "Rule: Blazers, jackets, coats, and sweaters must be classified as 'Outerwear', NOT 'Tops'."
)

# --- Functions ---

def get_system_prompt() -> str:
    """Reads the core Ahvi system prompt from the text file."""
    try:
        # Adjusted path to ensure it finds the file regardless of where you run it
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

def get_romanized_rewrite_prompt(english_text: str, lang_type: str) -> str:
    return (
        f"Rewrite this into natural, highly conversational {lang_type.upper()} (WhatsApp style): '{english_text}'\n"
        "RULES FOR REALISM AND HUMOR:\n"
        "1. Sound like a fun, slightly sassy fashion-forward best friend.\n"
        "2. Use casual filler words (like 'yaar', 'arey', 'literally', 'tbh') where appropriate for the language.\n"
        "3. Keep fashion terminology in English.\n"
        "4. Do not be overly polite or robotic. Add a touch of friendly sarcasm if they pick a boring outfit.\n"
        "5. No intro, no quotes, just the raw text."
    )

def get_outfit_naming_prompt(items_str: str) -> str:
    return f"Give a cool, short, 2-to-3 word aesthetic name for an outfit consisting of: {items_str}. Do not explain. Just output the name."

# Keep this for backward compatibility if other parts of your app use it
def get_memory_extraction_prompt(new_user_text: str, current_memory: str) -> str:
    return UPDATE_MEMORY_PROMPT.format(new_user_text=new_user_text, current_memory=current_memory)
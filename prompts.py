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

VISION_ANALYZE_PROMPT = (
    "You are an expert AI fashion categorizer. Analyze the main clothing item in the image and return ONLY a valid JSON object with these exact keys:\n"
    "1. 'name': A catchy, descriptive 2-to-3 word name for the item.\n"
    "2. 'category': MUST be exactly one of the following: 'Tops', 'Bottoms', 'Footwear', 'Outerwear', 'Accessories', 'Dresses'. (e.g., A dress MUST be 'Dresses', never 'Tops').\n"
    "3. 'sub_category': The specific type of garment (e.g., T-Shirt, Jeans, Saree, Kurta, Sneakers, Blazer, Maxi Dress).\n"
    "4. 'occasions': Think exhaustively! Provide a comprehensive list of ALL possible occasions where this garment could be worn. Give me AS MANY relevant occasions as possible (aim for 4 to 8) (e.g., [\"casual\", \"night out\", \"brunch\", \"date night\", \"vacation\", \"party\", \"loungewear\", \"office\", \"wedding guest\", \"festive\", \"streetwear\"]).\n"
    "5. 'pattern': The visual pattern or texture. If it is a solid color but has texture, mention the texture instead of just 'plain' (e.g., 'ribbed', 'pleated', 'striped', 'floral', 'checked', 'printed', 'sequined', 'embroidered', 'lace', 'velvet', 'plain').\n\n"
    "CRITICAL RULES:\n"
    "- Do not include markdown formatting, backticks, or conversational text. Output ONLY raw JSON.\n"
    "- The 'category' field is case-sensitive and MUST perfectly match one of the allowed options."
)

INTENT_ROUTER_PROMPT = (
    "You are Ahvi's routing brain. Analyze the user's message to determine if they want an outfit recommendation.\n\n"
    "CRITICAL RULES FOR CONTEXT:\n"
    "1. If the user's message contains ANY hint of an occasion, vibe, event, or style (even just 1 or 2 words like 'Brunch', 'Casual', 'Party', 'Office', or an emoji + word), you MUST set 'has_context' to true immediately.\n"
    "2. DO NOT interrogate the user. Never ask more than ONE clarifying question. Take whatever small hint they give you and proceed.\n"
    "3. ONLY set 'has_context' to false if the message is completely blank of details (e.g., 'Pick an outfit for me', 'What should I wear?').\n\n"
    "Output ONLY raw JSON with these exact keys:\n"
    "{\n"
    "  \"wants_outfit\": true or false,\n"
    "  \"has_context\": true or false,\n"
    "  \"occasion\": \"The exact vibe/occasion extracted from the user's text (e.g., 'Casual Brunch'). Null if missing.\",\n"
    "  \"clarifying_question\": \"A friendly question asking for the vibe (ONLY if has_context is false). Null otherwise.\",\n"
    "  \"chips\": [\"Array\", \"of\", \"3\", \"short\", \"options\"] (ONLY if has_context is false. Null otherwise.)\n"
    "}"
)

# --- Functions ---

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

def get_memory_extraction_prompt(new_user_text: str, current_memory: str) -> str:
    return UPDATE_MEMORY_PROMPT.format(new_user_text=new_user_text, current_memory=current_memory)
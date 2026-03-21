# backend/services/llm_service.py

import requests

# Pointing to your local Ollama instance
OLLAMA_URL = "http://localhost:11434/api"
DEFAULT_MODEL = "llama3.1"

def generate_text(prompt: str, options: dict = None) -> str:
    """
    Generates a single text completion. 
    Used by translation.py and memory updates.
    """
    payload = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    if options:
        payload["options"] = options

    try:
        response = requests.post(f"{OLLAMA_URL}/generate", json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"❌ LLM Error (generate_text): {e}")
        return ""

def chat_completion(messages: list, system_instruction: str = "") -> str:
    """
    Handles multi-turn chat completions.
    Used by the main text_chat endpoint in chat.py.
    """
    formatted_messages = []
    
    # Inject the system instructions (Personality, Rules, Memory)
    if system_instruction:
        formatted_messages.append({"role": "system", "content": system_instruction})
        
    # Append the recent chat history
    formatted_messages.extend(messages)

    payload = {
        "model": DEFAULT_MODEL,
        "messages": formatted_messages,
        "stream": False
    }

    try:
        response = requests.post(f"{OLLAMA_URL}/chat", json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"❌ LLM Error (chat_completion): {e}")
        return "Oops, my style brain glitched for a second! Can you repeat that?"

def format_wardrobe_for_llm(items):
    """
    Converts Appwrite documents into a text summary for the AI.
    """
    if not items:
        return "The user's wardrobe is currently empty."
    
    wardrobe_msg = "The user has the following items in their wardrobe:\n"
    for item in items:
        name = item.get('name', 'Item')
        color = item.get('color', '')
        category = item.get('category', '')
        wardrobe_msg += f"- {name} ({color} {category})\n"
    
    return wardrobe_msg
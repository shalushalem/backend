# backend/services/llm_service.py

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =========================
# CONFIG
# =========================
OLLAMA_URL = "http://localhost:11434/api"
DEFAULT_MODEL = "llama3.1"

# =========================
# SESSION WITH RETRIES
# =========================
session = requests.Session()

retries = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
)

session.mount("http://", HTTPAdapter(max_retries=retries))


# =========================
# SAFE REQUEST HANDLER
# =========================
def safe_request(endpoint: str, payload: dict, timeout: int = 30):
    try:
        response = session.post(f"{OLLAMA_URL}/{endpoint}", json=payload, timeout=timeout)

        if response.status_code != 200:
            print(f"\n🔥 OLLAMA ERROR ({endpoint}):")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            return None

        return response.json()

    except Exception as e:
        print(f"❌ LLM Request Failed ({endpoint}): {e}")
        return None


# =========================
# TEXT GENERATION
# =========================
def generate_text(prompt: str, options: dict = None) -> str:
    if not prompt:
        return "none"

    payload = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "stream": False
    }

    if options:
        payload["options"] = options

    data = safe_request("generate", payload, timeout=30)

    if not data:
        return "none"

    return data.get("response", "").strip() or "none"


# =========================
# CHAT COMPLETION
# =========================
def chat_completion(messages: list, system_instruction: str = "") -> str:

    if not messages:
        return "I didn't catch that!"

    formatted_messages = []

    # ✅ SYSTEM MESSAGE SAFETY
    if system_instruction:
        formatted_messages.append({
            "role": "system",
            "content": system_instruction[:8000]  # prevent overload
        })

    # ✅ LIMIT HISTORY SIZE
    safe_messages = messages[-10:]  # last 10 only

    for msg in safe_messages:
        role = msg.get("role", "user").lower()
        if role not in ["user", "assistant", "system"]:
            role = "assistant"

        content = str(msg.get("content", ""))[:4000]

        if content:
            formatted_messages.append({
                "role": role,
                "content": content
            })

    payload = {
        "model": DEFAULT_MODEL,
        "messages": formatted_messages,
        "stream": False
    }

    data = safe_request("chat", payload, timeout=45)

    if not data:
        return "I'm having trouble thinking right now 😅 Try again in a moment."

    try:
        return data.get("message", {}).get("content", "").strip() or "Something went wrong 😅"
    except Exception:
        return "AI response parsing failed 😅"


# =========================
# WARDROBE FORMATTER
# =========================
def format_wardrobe_for_llm(items):
    if not items:
        return "The user's wardrobe is currently empty."

    wardrobe_msg = "The user has the following items in their wardrobe:\n"

    for item in items[:50]:  # ✅ LIMIT SIZE
        name = item.get('name', 'Item')
        color = item.get('color', '')
        category = item.get('category', '')
        wardrobe_msg += f"- {name} ({color} {category})\n"

    return wardrobe_msg
import requests

URL_GENERATE = "http://localhost:11434/api/generate"
URL_CHAT = "http://localhost:11434/api/chat"

def generate_text(prompt: str, model: str = "llama3.1", options: dict = None) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    if options:
        payload["options"] = options
    try:
        response = requests.post(URL_GENERATE, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"LLM Generate Error: {e}")
        return ""

def chat_completion(messages: list, system_instruction: str, model: str = "llama3.1") -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_instruction}] + messages,
        "stream": False
    }
    try:
        response = requests.post(URL_CHAT, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"LLM Chat Error: {e}")
        return ""
from typing import Dict, Any
from brain.intents.ahvi_mode_router import detect_ahvi_mode

def contains_any(text: str, words: list) -> bool:
    return any(word in text for word in words)


def extract_signals(text: str) -> Dict[str, bool]:
    t = text.lower()

    return {
        "user_asks_should_i_buy": contains_any(t, ["should i buy", "worth it", "do i need this"]),
        "user_requests_compare": contains_any(t, ["compare", "vs", "versus"]),
        "user_requests_style_with_it": contains_any(t, ["style this", "wear this with"]),
        "user_requests_board": contains_any(t, ["board", "style board", "mood board"]),
        "user_requests_packing_list": contains_any(t, ["packing list", "what to pack"]),
        "user_mentions_budget": contains_any(t, ["budget", "cheap", "affordable"]),
        "user_mentions_color": contains_any(t, ["black", "white", "red", "blue"]),
        "user_mentions_category": contains_any(t, ["dress", "shirt", "jeans", "heels"]),
        "user_mentions_occasion": contains_any(t, ["wedding", "party", "office"]),
        "user_mentions_wardrobe": contains_any(t, ["wardrobe", "closet"]),
    }


def detect_mode(text: str) -> str:
    t = text.lower()

    if contains_any(t, ["wear", "outfit", "style", "dress"]):
        return "style"

    if contains_any(t, ["plan", "trip", "pack", "schedule"]):
        return "plan"

    if contains_any(t, ["organize", "todo", "groceries"]):
        return "organize"

    return "general"


def detect_domain(text: str, mode: str, signals: Dict) -> str:
    t = text.lower()

    if mode == "style":
        if signals["user_asks_should_i_buy"] or signals["user_requests_compare"]:
            return "shopping"
        return "styling"

    if mode == "plan":
        if signals["user_requests_packing_list"]:
            return "packing"
        if contains_any(t, ["trip", "travel"]):
            return "travel"
        return "planning"

    if mode == "organize":
        if contains_any(t, ["wardrobe", "closet"]):
            return "wardrobe"
        if contains_any(t, ["groceries"]):
            return "groceries"
        return "tasks"

    return "general"


def classify_intent(text: str) -> Dict[str, Any]:
    signals = extract_signals(text)
    mode = detect_mode(text)
    domain = detect_domain(text, mode, signals)

    board_hint = None
    if signals["user_requests_board"]:
        if domain == "packing":
            board_hint = "packing_list"
        elif mode == "style":
            board_hint = "style_board"
        else:
            board_hint = "board"

    return {
        "intent": domain,
        "mode": mode,
        "domain": domain,
        "signals": signals,
        "board_hint": board_hint,
        "confidence": 0.9
    }
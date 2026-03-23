from typing import Dict, List, Any


# =========================
# HELPERS
# =========================
def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value.keys()) > 0
    return True


def missing(slots: Dict, key: str) -> bool:
    return not has_value(slots.get(key))


def push_if_missing(output: List[str], slots: Dict, key: str, label: str = None):
    label = label or key
    if missing(slots, key) and label not in output:
        output.append(label)


# =========================
# STYLE
# =========================
def get_styling_missing(classified: Dict) -> List[str]:
    slots = classified.get("slots", {})
    signals = classified.get("signals", {})
    text = str(slots.get("raw_text", "")).lower()

    out = []

    is_accessory = (
        signals.get("user_requests_style_with_it") or
        "style this" in text or
        "wear this with" in text
    )

    is_occasion = (
        signals.get("user_mentions_occasion") or
        "what should i wear" in text or
        "outfit for" in text
    )

    if is_accessory:
        push_if_missing(out, slots, "item_type", "item category")
        push_if_missing(out, slots, "occasion", "occasion")
        push_if_missing(out, slots, "vibe", "vibe")
        return out[:2]

    if is_occasion:
        push_if_missing(out, slots, "occasion")
        push_if_missing(out, slots, "weather")
        push_if_missing(out, slots, "vibe")
        return out[:2]

    push_if_missing(out, slots, "occasion")
    push_if_missing(out, slots, "item_type", "item category")
    push_if_missing(out, slots, "vibe")

    return out[:2]


# =========================
# SHOPPING
# =========================
def get_shopping_missing(classified: Dict) -> List[str]:
    slots = classified.get("slots", {})
    signals = classified.get("signals", {})
    text = str(slots.get("raw_text", "")).lower()

    out = []

    if "compare" in text:
        push_if_missing(out, slots, "item_1", "first item")
        push_if_missing(out, slots, "item_2", "second item")
        return out[:2]

    if "dupe" in text:
        push_if_missing(out, slots, "item_type", "item category")
        push_if_missing(out, slots, "budget", "budget")
        return out[:2]

    push_if_missing(out, slots, "item_type", "item category")
    push_if_missing(out, slots, "budget", "budget")

    return out[:2]


# =========================
# PACKING
# =========================
def get_packing_missing(classified: Dict) -> List[str]:
    slots = classified.get("slots", {})
    out = []

    push_if_missing(out, slots, "destination")
    push_if_missing(out, slots, "duration", "trip duration")
    push_if_missing(out, slots, "weather")

    return out[:2]


# =========================
# TRAVEL
# =========================
def get_travel_missing(classified: Dict) -> List[str]:
    slots = classified.get("slots", {})
    out = []

    push_if_missing(out, slots, "destination")
    push_if_missing(out, slots, "dates")
    push_if_missing(out, slots, "budget")

    return out[:2]


# =========================
# MAIN
# =========================
def missing_slots(classified: Dict) -> List[str]:

    mode = classified.get("mode", "general")
    domain = classified.get("domain", "general")

    if mode == "style" and domain == "styling":
        return get_styling_missing(classified)

    if mode == "style" and domain == "shopping":
        return get_shopping_missing(classified)

    if mode == "plan" and domain == "packing":
        return get_packing_missing(classified)

    if mode == "plan" and domain == "travel":
        return get_travel_missing(classified)

    return []
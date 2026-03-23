from typing import Dict, List


# =========================
# TYPES (informal)
# =========================
AhviMode = str  # "style" | "plan" | "organize" | "general"


# =========================
# KEYWORDS
# =========================
STYLE_KEYWORDS = [
    "outfit", "wear", "style", "match", "pair", "look", "dress",
    "color", "colour", "shoes", "bag", "accessories", "jewellery",
    "heels", "wardrobe gap", "what should i wear", "style this",
    "what goes with"
]

SHOPPING_STYLE_KEYWORDS = [
    "buy", "shop", "worth it", "compare", "dupe",
    "cart", "checkout", "should i buy", "is this worth it",
    "what should i buy"
]

PLAN_KEYWORDS = [
    "plan", "trip", "travel", "pack", "packing", "packing list",
    "schedule", "event", "itinerary", "workout", "diet",
    "routine", "calendar", "vacation", "holiday"
]

ORGANIZE_KEYWORDS = [
    "organize", "organise", "wardrobe", "closet", "declutter",
    "sort", "inventory", "groceries", "grocery list",
    "shopping list", "tasks", "todo", "to-do", "checklist"
]


# =========================
# HELPERS
# =========================
def find_matches(text: str, words: List[str]) -> List[str]:
    return [word for word in words if word in text]


def score_matches(matches: List[str]) -> float:
    if len(matches) == 0:
        return 0
    if len(matches) == 1:
        return 0.7
    if len(matches) == 2:
        return 0.85
    return 0.95


# =========================
# MAIN FUNCTION
# =========================
def detect_ahvi_mode(text: str) -> Dict:

    lower = (text or "").lower()

    style_matches = (
        find_matches(lower, STYLE_KEYWORDS) +
        find_matches(lower, SHOPPING_STYLE_KEYWORDS)
    )

    plan_matches = find_matches(lower, PLAN_KEYWORDS)
    organize_matches = find_matches(lower, ORGANIZE_KEYWORDS)

    scores = {
        "style": score_matches(style_matches),
        "plan": score_matches(plan_matches),
        "organize": score_matches(organize_matches),
        "general": 0.5,
    }

    matched_keywords = {
        "style": style_matches,
        "plan": plan_matches,
        "organize": organize_matches,
        "general": [],
    }

    # =========================
    # PRIORITY LOGIC
    # =========================

    # Style wins if strong signal
    if (
        scores["style"] >= 0.7 and
        scores["style"] >= scores["plan"] and
        scores["style"] >= scores["organize"]
    ):
        return {
            "mode": "style",
            "confidence": scores["style"],
            "scores": scores,
            "matchedKeywords": matched_keywords
        }

    # Plan wins next
    if scores["plan"] >= 0.7 and scores["plan"] >= scores["organize"]:
        return {
            "mode": "plan",
            "confidence": scores["plan"],
            "scores": scores,
            "matchedKeywords": matched_keywords
        }

    # Organize
    if scores["organize"] >= 0.7:
        return {
            "mode": "organize",
            "confidence": scores["organize"],
            "scores": scores,
            "matchedKeywords": matched_keywords
        }

    # Default
    return {
        "mode": "general",
        "confidence": 0.5,
        "scores": scores,
        "matchedKeywords": matched_keywords
    }
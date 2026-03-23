import re
from typing import Dict, Any, List


# =========================
# WORD LISTS
# =========================
COLOR_WORDS = ["black","white","red","blue","green","pink","beige","brown","grey","gray","navy","cream","yellow","orange","purple","maroon","burgundy","olive","gold","silver"]

CATEGORY_WORDS = ["dress","dresses","top","tops","shirt","shirts","t-shirt","tee","blouse","blouses","skirt","skirts","pants","trousers","jeans","shorts","jacket","blazer","coat","kurta","saree","lehenga","heels","shoes","sneakers","sandals","bag","clutch","boots","hoodie","sweater","cardigan","set"]

OCCASION_WORDS = ["wedding","brunch","dinner","party","office","airport","vacation","trip","cocktail","date","work","college","sangeet","haldi","mehendi","reception","festival","birthday","meeting"]

VIBE_WORDS = ["casual","formal","elegant","chic","edgy","minimal","feminine","romantic","bold","classy","sporty","relaxed","polished","glam","soft","clean"]

DESTINATION_HINTS = ["goa","dubai","london","paris","bali","mumbai","hyderabad","delhi","bangalore","new york","singapore","tokyo","maldives","ooty","manali","jaipur"]

TRIP_TYPE_WORDS = ["beach","work trip","business trip","vacation","holiday","wedding trip","family trip","solo trip","girls trip","honeymoon"]

ORGANIZE_WORDS = ["wardrobe","closet","groceries","shopping list","tasks","todo","checklist"]

DIET_WORDS = ["vegetarian","vegan","high protein","keto","jain","eggless"]

MONTHS = ["january","february","march","april","may","june","july","august","september","october","november","december"]


# =========================
# HELPERS
# =========================
def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def find_first(text: str, values: List[str]):
    return next((v for v in values if v in text), None)


def find_all(text: str, values: List[str]):
    return [v for v in values if v in text]


def extract_duration(text: str):
    patterns = [
        r"\bfor (\d+)\s*(day|days|night|nights|week|weeks)\b",
        r"\b(\d+)\s*(day|days|night|nights|week|weeks)\b",
        r"\bweekend\b"
    ]

    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def extract_budget(text: str):
    m = re.search(r"(₹|rs|inr|\$)\s*\d+", text)
    return m.group(0) if m else None


def extract_date(text: str):
    for m in MONTHS:
        if m in text:
            return m
    if "today" in text or "tomorrow" in text:
        return "relative"
    return None


def extract_destination(text: str):
    return find_first(text, DESTINATION_HINTS)


# =========================
# MAIN
# =========================
def extract_slots(text: str) -> Dict[str, Any]:

    t = normalize(text)

    slots = {"raw_text": text}

    color = find_first(t, COLOR_WORDS)
    if color:
        slots["item_color"] = color

    categories = find_all(t, CATEGORY_WORDS)
    if categories:
        slots["item_type"] = categories[0]
        slots["item_categories"] = categories

    occasion = find_first(t, OCCASION_WORDS)
    if occasion:
        slots["occasion"] = occasion

    vibe = find_first(t, VIBE_WORDS)
    if vibe:
        slots["vibe"] = vibe

    destination = extract_destination(t)
    if destination:
        slots["destination"] = destination

    duration = extract_duration(t)
    if duration:
        slots["duration"] = duration

    date = extract_date(t)
    if date:
        slots["dates"] = date

    trip_type = find_first(t, TRIP_TYPE_WORDS)
    if trip_type:
        slots["trip_type"] = trip_type

    budget = extract_budget(t)
    if budget:
        slots["budget"] = budget

    diet = find_first(t, DIET_WORDS)
    if diet:
        slots["diet"] = diet

    focus = find_first(t, ORGANIZE_WORDS)
    if focus:
        slots["focus_category"] = focus

    # flags
    if "board" in t:
        slots["board_requested"] = True

    if "packing list" in t:
        slots["packing_list_requested"] = True

    if any(x in t for x in ["compare", "vs", "versus"]):
        slots["compare_requested"] = True

    return slots
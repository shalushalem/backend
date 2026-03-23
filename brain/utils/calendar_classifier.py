from typing import Dict, Any, List


# =========================
# RULES
# =========================
RULES = [
    {"group": "travel", "subtype": "domestic_flight", "keywords": ["flight", "airport", "boarding"], "priority": "critical"},
    {"group": "travel", "subtype": "international_flight", "keywords": ["international flight", "passport", "immigration"], "priority": "critical"},
    {"group": "travel", "subtype": "train", "keywords": ["train", "station", "pnr", "platform"], "priority": "important"},
    {"group": "travel", "subtype": "hotel_checkin", "keywords": ["hotel check in", "hotel check-in"], "priority": "important"},

    {"group": "work", "subtype": "work_meeting", "keywords": ["meeting", "sync", "review", "client call", "1:1"], "priority": "important"},
    {"group": "work", "subtype": "presentation", "keywords": ["presentation", "pitch", "demo", "deck"], "priority": "critical"},
    {"group": "work", "subtype": "interview", "keywords": ["interview", "hr round", "technical round"], "priority": "critical"},

    {"group": "school", "subtype": "parent_teacher_meeting", "keywords": ["ptm", "parent teacher meeting"], "priority": "important"},
    {"group": "school", "subtype": "annual_day", "keywords": ["annual day", "school performance"], "priority": "important"},
    {"group": "school", "subtype": "sports_day", "keywords": ["sports day", "athletics", "race day"], "priority": "important"},

    {"group": "kids", "subtype": "kids_birthday_party", "keywords": ["kids birthday", "party invite"], "priority": "important"},
    {"group": "kids", "subtype": "pickup_drop", "keywords": ["pickup", "drop off", "pick up"], "priority": "important"},

    {"group": "social", "subtype": "birthday_party", "keywords": ["birthday", "birthday party"], "priority": "important"},
    {"group": "social", "subtype": "dinner", "keywords": ["dinner", "dinner plans"], "priority": "light"},
    {"group": "social", "subtype": "brunch", "keywords": ["brunch"], "priority": "light"},
    {"group": "social", "subtype": "cocktail", "keywords": ["cocktail", "cocktail party"], "priority": "important"},
    {"group": "social", "subtype": "wedding", "keywords": ["wedding", "shaadi", "nikah", "reception"], "priority": "important"},

    {"group": "health", "subtype": "doctor_appointment", "keywords": ["doctor", "consultation", "physician"], "priority": "critical"},
    {"group": "health", "subtype": "lab_test", "keywords": ["blood test", "lab test", "scan", "xray", "mri"], "priority": "critical"},

    {"group": "fitness", "subtype": "gym_class", "keywords": ["gym", "workout", "training session"], "priority": "light"},
    {"group": "fitness", "subtype": "yoga", "keywords": ["yoga"], "priority": "light"},
    {"group": "fitness", "subtype": "pilates", "keywords": ["pilates"], "priority": "light"},

    {"group": "beauty", "subtype": "salon_appointment", "keywords": ["salon", "hair appointment", "facial", "nails"], "priority": "important"},

    {"group": "finance", "subtype": "electricity_bill", "keywords": ["electricity bill", "power bill", "eb bill"], "priority": "critical"},
    {"group": "finance", "subtype": "water_bill", "keywords": ["water bill"], "priority": "critical"},
    {"group": "finance", "subtype": "internet_bill", "keywords": ["internet bill", "wifi bill", "broadband"], "priority": "critical"},
    {"group": "finance", "subtype": "mobile_bill", "keywords": ["mobile bill", "phone bill", "recharge due"], "priority": "critical"},
    {"group": "finance", "subtype": "credit_card_bill", "keywords": ["credit card bill", "minimum due", "card due"], "priority": "critical"},
    {"group": "finance", "subtype": "rent_payment", "keywords": ["rent", "house rent", "apartment rent"], "priority": "critical"},
    {"group": "finance", "subtype": "loan_emi", "keywords": ["emi", "loan payment", "installment"], "priority": "critical"},
    {"group": "finance", "subtype": "subscription_payment", "keywords": ["subscription", "netflix", "spotify", "prime", "icloud"], "priority": "important"},
    {"group": "finance", "subtype": "school_fee_payment", "keywords": ["school fees", "fee payment", "tuition fees"], "priority": "critical"},
]


# =========================
# HELPERS
# =========================
def normalize(event: Dict[str, Any]) -> str:
    return " ".join(filter(None, [
        event.get("title"),
        event.get("notes"),
        event.get("venueName"),
        event.get("venueAddress"),
        event.get("dressCode"),
    ])).lower()


def score_rule(text: str, rule: Dict) -> (float, List[str]):
    signals = [kw for kw in rule["keywords"] if kw.lower() in text]
    if not signals:
        return 0, []

    score = min(0.55 + len(signals) * 0.12, 0.94)
    if text.startswith(rule["keywords"][0]):
        score += 0.03

    return min(score, 0.97), signals


def classify_event_advanced(event: Dict[str, Any]) -> Dict[str, Any]:
    text = normalize(event)

    best = None
    best_score = 0
    matched_signals = []

    for rule in RULES:
        score, signals = score_rule(text, rule)

        if score > best_score:
            best = rule
            best_score = score
            matched_signals = signals

    if not best:
        return {
            **event,
            "group": "miscellaneous",
            "subtype": "generic_event",
            "confidenceScore": 0.3,
            "matchedSignals": [],
            "missingFields": [],
            "needsUserConfirmation": True,
            "priority": "light",
        }

    return {
        **event,
        "group": best["group"],
        "subtype": best["subtype"],
        "confidenceScore": round(best_score, 2),
        "matchedSignals": matched_signals,
        "missingFields": [],
        "needsUserConfirmation": best_score < 0.45,
        "priority": best["priority"],
    }
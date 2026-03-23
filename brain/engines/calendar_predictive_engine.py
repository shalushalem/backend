from datetime import datetime, timedelta


# =========================
# PREP TASKS
# =========================
def build_prep_tasks(event):
    tasks = set()
    group = event.get("group")
    subtype = event.get("subtype")

    if group == "travel":
        tasks.update(["Check documents", "Pack essentials", "Set alarm", "Leave with buffer"])

    elif group == "social":
        tasks.add("Decide outfit")
        if subtype in ["wedding", "birthday_party", "cocktail"]:
            tasks.add("Check shoes and bag")

    elif group in ["kids", "school"]:
        tasks.update(["Pack child items", "Confirm pickup/reporting time"])

    elif group == "health":
        tasks.update(["Keep reports ready", "Leave with buffer"])
        if subtype == "lab_test":
            tasks.add("Check fasting instructions")

    elif group == "finance":
        tasks.update(["Keep payment method ready", "Clear before due window"])

    elif group == "work":
        if subtype in ["presentation", "interview"]:
            tasks.update(["Review deck/CV", "Charge laptop", "Set outfit aside"])
        else:
            tasks.add("Review agenda")

    else:
        tasks.add("Quick prep check")

    if event.get("dressCode"):
        tasks.add(f"Dress code: {event['dressCode']}")

    return list(tasks)


# =========================
# PACKING
# =========================
def build_packing_list(event):
    mapping = {
        "domestic_flight": ["ID", "Phone", "Wallet", "Charger", "Tickets"],
        "international_flight": ["Passport", "Visa", "Wallet", "Tickets"],
        "doctor_appointment": ["Reports", "ID"],
        "presentation": ["Laptop", "Charger", "Deck"],
    }
    return mapping.get(event.get("subtype"), [])


# =========================
# OUTFIT
# =========================
def build_outfit(event):
    rules = {
        "presentation": ["structured", "clean", "confident"],
        "wedding": ["event-ready", "occasionwear"],
        "gym_class": ["activewear", "breathable"],
    }

    subtype = event.get("subtype")
    if subtype in rules:
        return {
            "outfitKeywords": rules[subtype]
        }

    return None


# =========================
# BUFFER PLAN
# =========================
def build_buffer(event):
    try:
        start = datetime.fromisoformat(event.get("startAtISO"))
    except:
        return None

    leave_minutes = 30

    if event.get("group") == "travel":
        leave_minutes = 120

    leave_by = start - timedelta(minutes=leave_minutes)

    return {
        "leaveByISO": leave_by.isoformat()
    }


# =========================
# STRESS SCORE
# =========================
def compute_stress(event):
    score = 20

    if event.get("priority") == "critical":
        score += 25

    if event.get("group") == "travel":
        score += 20

    if event.get("subtype") in ["wedding", "presentation"]:
        score += 15

    return min(score, 100)


# =========================
# FOLLOWUPS
# =========================
def build_followups(event):
    subtype = event.get("subtype")
    followups = []

    if "flight" in subtype:
        followups.append("Check hotel")

    if subtype == "interview":
        followups.append("Send follow-up email")

    return followups


# =========================
# MAIN ENGINE
# =========================
def run_calendar_predictive_engine(event, preferences=None):

    return {
        "prepTasks": build_prep_tasks(event),
        "packingList": build_packing_list(event),
        "outfitPrompt": build_outfit(event),
        "bufferPlan": build_buffer(event),
        "stressLoadScore": compute_stress(event),
        "followupCandidates": build_followups(event),
        "linkedErrands": []
    }
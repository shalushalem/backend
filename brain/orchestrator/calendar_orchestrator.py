from typing import List, Dict, Any
from datetime import datetime

# 🧠 ENGINES
from brain.utils.calendar_classifier import classify_event_advanced
from brain.engines.calendar_predictive_engine import run_calendar_predictive_engine
from brain.utils.calendar_formatter import build_calendar_checklist_bundle
from brain.utils.calendar_reminders import build_calendar_reminders
from brain.utils.day_briefing import (
    build_morning_briefing,
    build_evening_briefing,
    build_best_day_briefing
)
from brain.utils.family_layer import build_responsibility_map, generate_family_prompts


# =========================
# HELPERS
# =========================
def build_event_object(event: Dict) -> Dict:
    """
    Normalize event → ensures required fields exist
    """
    return {
        "title": event.get("title", ""),
        "group": event.get("group"),
        "subtype": event.get("subtype"),
        "priority": event.get("priority", "important"),

        # 🔥 critical for predictive engine
        "startAtISO": event.get("startAtISO") or datetime.now().isoformat(),

        # optional
        "autoPayEnabled": event.get("autoPayEnabled", False),
        "amount": event.get("amount")
    }


# =========================
# SINGLE EVENT PIPELINE
# =========================
def run_calendar_runtime(event: Dict, preferences: Dict = None) -> Dict[str, Any]:

    # 🧠 1. CLASSIFICATION
    classified = classify_event_advanced(event)

    # 🧱 2. BUILD FULL EVENT (CRITICAL FIX)
    full_event = build_event_object({
        **event,
        **classified
    })

    # 🔮 3. PREDICTIVE ENGINE (FIXED)
    predictive = run_calendar_predictive_engine(full_event, preferences)

    # 🎨 4. CHECKLIST
    checklist = build_calendar_checklist_bundle(
        classified,
        {
            "packing": predictive.get("packingList", []),
            "prep_tasks": predictive.get("prepTasks", []),
            "outfit": predictive.get("outfitPrompt", {})
        }
    )

    # ⏰ 5. REMINDERS (ADDED)
    reminders = build_calendar_reminders(
        full_event,
        checklist,
        preferences
    )

    # 👨‍👩‍👧‍👦 6. FAMILY
    responsibilities = build_responsibility_map(classified)
    family_prompts = generate_family_prompts(classified, responsibilities)

    # 🧾 7. BRIEFING HINT
    hint = []

    buffer_plan = predictive.get("bufferPlan", {})
    if buffer_plan.get("leaveByISO"):
        hint.append(f"Leave by {buffer_plan['leaveByISO']}")

    if predictive.get("prepTasks"):
        hint.append(predictive["prepTasks"][0])

    return {
        "classifiedEvent": classified,
        "predictiveOutput": predictive,
        "checklistBundle": checklist,
        "reminders": reminders,
        "responsibilities": responsibilities,
        "familyPrompts": family_prompts,
        "dayBriefingHint": hint
    }


# =========================
# DAILY PIPELINE
# =========================
def run_daily_calendar_runtime(events: List[Dict], preferences: Dict = None) -> Dict:

    results = [
        run_calendar_runtime(e, preferences)
        for e in events
    ]

    return {
        "results": results,
        "morningBriefing": build_morning_briefing(results),
        "eveningBriefing": build_evening_briefing(results),
        "bestBriefing": build_best_day_briefing(results)
    }
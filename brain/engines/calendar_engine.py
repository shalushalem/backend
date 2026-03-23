from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import traceback

from middleware.auth_middleware import get_current_user

# 🔥 NEW: use orchestrator (NOT engine)
from brain.orchestrator.calendar_orchestrator import (
    run_calendar_runtime,
    run_daily_calendar_runtime
)

router = APIRouter()


# =========================
# REQUEST MODELS
# =========================
class CalendarEventRequest(BaseModel):
    text: str = Field(..., min_length=2)


class DailyEventsRequest(BaseModel):
    events: list  # list of event dicts


# =========================
# SINGLE EVENT PIPELINE
# =========================
@router.post("/calendar/process")
def process_event(
    req: CalendarEventRequest,
    user=Depends(get_current_user)
):
    try:
        user_id = user["user_id"]

        event = {
            "title": req.text,
            "user_id": user_id
        }

        # 🔥 MASTER PIPELINE
        result = run_calendar_runtime(event)

        return {
            "success": True,
            "meta": {"user_id": user_id},
            "data": result
        }

    except Exception:
        print("❌ /calendar/process error:\n", traceback.format_exc())
        raise HTTPException(500, "Calendar processing failed")


# =========================
# DAILY BRIEFING PIPELINE
# =========================
@router.post("/calendar/daily")
def daily_briefing(
    req: DailyEventsRequest,
    user=Depends(get_current_user)
):
    try:
        user_id = user["user_id"]

        # attach user_id to all events
        events = [
            {**event, "user_id": user_id}
            for event in req.events
        ]

        result = run_daily_calendar_runtime(events)

        return {
            "success": True,
            "data": result
        }

    except Exception:
        print("❌ /calendar/daily error:\n", traceback.format_exc())
        raise HTTPException(500, "Daily briefing failed")


# =========================
# HEALTH CHECK
# =========================
@router.get("/calendar/health")
def calendar_health():
    return {
        "status": "ok",
        "engine": "calendar_orchestrator_v1",
        "auth": "enabled",
        "mode": "pipeline",
        "ready": True
    }
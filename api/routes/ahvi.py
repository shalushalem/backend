# backend/api/routes/ahvi.py

from fastapi import APIRouter
from pydantic import BaseModel

from brain.orchestrator import ahvi_orchestrator

router = APIRouter()


class ChatRequest(BaseModel):
    text: str
    user_id: str | None = None
    context: dict | None = None


@router.post("/ahvi/chat")
def chat(req: ChatRequest):

    result = ahvi_orchestrator.run(
        text=req.text,
        user_id=req.user_id,
        context=req.context or {}
    )

    return result
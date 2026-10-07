from fastapi import APIRouter
from pydantic import BaseModel

from ai.copilot import ShoppingCopilot


router = APIRouter(
    prefix="/copilot",
    tags=["AI Copilot"]
)

copilot = ShoppingCopilot()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/chat")
async def chat(request: ChatRequest):

    result = await copilot.chat(
        request.message,
        request.session_id
    )

    return {
        "success": True,
        "response": result["response"],
        "intent": result.get("intent"),
        "session_intent": result.get("session_intent"),
        "tool": result.get("tool"),
        "recommendations": result["recommendations"]
    }
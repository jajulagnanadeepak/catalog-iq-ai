from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from ai.copilot import ShoppingCopilot


router = APIRouter(
    prefix="/copilot",
    tags=["AI Copilot"]
)

copilot = ShoppingCopilot()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        return value

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Session ID cannot be empty.")
        return value


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
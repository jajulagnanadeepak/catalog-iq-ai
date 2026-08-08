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


@router.post("/chat")
async def chat(request: ChatRequest):

    result = await copilot.chat(request.message)

    return {
        "success": True,
        "response": result["response"],
        "recommendations": result["recommendations"]
    }
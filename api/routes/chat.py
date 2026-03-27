from fastapi import APIRouter
from api.models import ChatRequest, APIResponse
from agent.rag_agent import run_agent

router = APIRouter()

@router.post("/chat", response_model=APIResponse)
async def chat(request: ChatRequest):
    if not request.question.strip():
        return APIResponse(status="error", error="Question cannot be empty")
    try:
        result = await run_agent(request.question, request.selected_text)
        return APIResponse(status="ok", data=result)
    except Exception as e:
        return APIResponse(status="error", error=str(e))

from fastapi import APIRouter
from api.models import ChatRequest, APIResponse, ChatData, Source
from agent.rag_agent import run_agent

router = APIRouter()

@router.post("/chat", response_model=APIResponse)
async def chat(request: ChatRequest):
    """Chat endpoint: Cohere embed → Qdrant search → Agent writes answer."""
    if not request.question.strip():
        return APIResponse(status="error", error="Question cannot be empty")
    try:
        result = await run_agent(request.question, request.selected_text)
        # Properly wrap sources as Source objects
        sources = []
        for s in result.get("sources", []):
            sources.append(Source(
                chapter_name=s.get("chapter_name", "Unknown"),
                source_url=s.get("source_url", ""),
                score=s.get("score", 0.0)
            ))
        return APIResponse(
            status="ok",
            data=ChatData(answer=result["answer"], sources=sources)
        )
    except Exception as e:
        return APIResponse(status="error", error=str(e))

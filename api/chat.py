"""Optimized Chat Endpoint"""
from fastapi import APIRouter
import time
from .models import ChatRequest, APIResponse, ChatData

router = APIRouter()

@router.post("/chat", response_model=APIResponse)
async def chat_endpoint(request: ChatRequest):
    start_time = time.time()
    try:
        from agent.rag_agent import run_agent
        result = await run_agent(question=request.question, selected_text=request.selected_text, use_cache=True)
        return APIResponse(status="ok", data=ChatData(answer=result["answer"], sources=result.get("sources", [])))
    except Exception as e:
        return APIResponse(status="error", error=str(e))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@router.get("/stats")
async def get_stats():
    from agent.rag_agent import _response_cache, _context_cache, _PRECOMPUTED_ANSWERS
    return {"response_cache_size": len(_response_cache), "context_cache_size": len(_context_cache), "precomputed_answers": len(_PRECOMPUTED_ANSWERS), "timestamp": time.time()}

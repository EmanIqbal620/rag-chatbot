"""
FastAPI Server for Hugging Face Spaces Deployment
Serves the full RAG Chatbot API with Cohere + Qdrant retrieval
"""
import os
import sys
from pathlib import Path

# Add backend to Python path so imports work on HF
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from HF Secrets
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Humanoid Robotics RAG Chatbot API",
    description="Full RAG pipeline: Cohere embeddings + Qdrant vector search + LLM generation",
    version="2.0.0"
)

# CORS — allow all origins for HF deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include API routes
from api.routes.chat import router as chat_router
from api.routes.ingest import router as ingest_router

app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(ingest_router, prefix="/api/v1", tags=["ingestion"])


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API info."""
    from agent.rag_agent import _PRECOMPUTED_ANSWERS
    return {
        "message": "Humanoid Robotics RAG Chatbot API",
        "version": "2.0.0",
        "pipeline": "Cohere Embed → Qdrant Vector Search → LLM Generation",
        "precomputed_answers": len(_PRECOMPUTED_ANSWERS)
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check."""
    import time
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "fastapi": "running",
            "cohere": "configured" if os.getenv("COHERE_API_KEY") else "missing",
            "qdrant": "configured" if os.getenv("QDRANT_URL") else "missing",
        }
    }


@app.get("/stats", tags=["stats"])
async def stats():
    """RAG pipeline stats."""
    import time
    from agent.rag_agent import _response_cache, _context_cache, _PRECOMPUTED_ANSWERS

    # Check Qdrant connection
    qdrant_status = "unknown"
    try:
        from retrieval.retriever import qdrant, QDRANT_AVAILABLE, COLLECTION
        if QDRANT_AVAILABLE:
            qdrant_status = f"connected (collection: {COLLECTION})"
        else:
            qdrant_status = "not available"
    except Exception as e:
        qdrant_status = f"error: {str(e)}"

    return {
        "response_cache_size": len(_response_cache),
        "context_cache_size": len(_context_cache),
        "precomputed_answers_count": len(_PRECOMPUTED_ANSWERS),
        "qdrant": qdrant_status,
        "cohere_api_key": "set" if os.getenv("COHERE_API_KEY") else "missing",
        "timestamp": time.time()
    }

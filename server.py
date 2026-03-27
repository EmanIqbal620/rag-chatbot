import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import chat router directly
from api.chat import router as chat_router

# Create FastAPI app
app = FastAPI(
    title="Humanoid Robotics RAG API",
    description="RAG API for the Humanoid Robotics AI textbook - Ultra Fast with Caching",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "Humanoid Robotics RAG API is running",
        "version": "2.0.0",
        "features": ["Pre-computed answers", "Multi-level caching", "Fast responses"]
    }

@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "healthy", "timestamp": __import__('time').time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    )

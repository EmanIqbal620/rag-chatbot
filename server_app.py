from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the components directly
from api.chat import router as chat_router
from utils.logging import setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Humanoid Robotics RAG API",
    description="RAG API for the Humanoid Robotics AI textbook using OpenAI Agents SDK",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, configure this properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

# Add startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Initializing services...")

    # Import here to avoid circular dependencies
    from database.postgres_client import PostgresService
    from agents.rag_agent import RAGAgent

    # Initialize postgres service
    postgres_service = app.state.postgres_service = PostgresService()
    await postgres_service.initialize()

    # Initialize RAG agent
    app.state.rag_agent = RAGAgent()

    logger.info("Services initialized successfully")

# Add shutdown event to cleanup
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    logger.info("Shutting down services...")

    # Close postgres connection pool
    if hasattr(app.state, 'postgres_service'):
        await app.state.postgres_service.close()

    # Cleanup RAG agent
    if hasattr(app.state, 'rag_agent'):
        app.state.rag_agent.cleanup()

    logger.info("Services shut down successfully")

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "Humanoid Robotics RAG API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server_app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
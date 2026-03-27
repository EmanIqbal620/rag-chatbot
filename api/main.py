import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.routes.chat import router as chat_router
from api.routes.ingest import router as ingest_router

load_dotenv("/mnt/d/Humanoid-Robotics-AI-textbook/backend/.env")

app = FastAPI(title="Humanoid AI Book RAG Chatbot API", version="1.0.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://humanoid-robotics-textbook-zeta.vercel.app").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Humanoid AI Book RAG Chatbot"}

#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server
Deploy to Hugging Face Inference Endpoints
"""

import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from huggingface_hub import InferenceClient

# Initialize FastAPI app
app = FastAPI(
    title="Humanoid Robotics MCP Server",
    description="AI Chatbot Backend with Model Context Protocol",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://huggingface.co",
        "https://*.hf.space",
        "http://localhost:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load MCP Configuration
MCP_CONFIG = {
    "version": "1.0",
    "model": {
        "name": "mistralai/Mistral-7B-Instruct-v0.2",
        "max_tokens": 500,
        "temperature": 0.7,
        "top_p": 0.95
    },
    "system_prompt": """You are an expert AI tutor for Humanoid Robotics. 
Help students learn:
- ROS 2 (Robot Operating System)
- Simulation & Digital Twins (Gazebo, Unity)
- AI for Robotics (NVIDIA Isaac)
- Vision-Language-Action Systems
- Hardware Requirements

Be concise, accurate, and encouraging. Cite sources when possible."""
}

# Initialize HF Client
HF_TOKEN = os.getenv("HF_TOKEN", "")
hf_client = InferenceClient(token=HF_TOKEN) if HF_TOKEN else None

# Request/Response Models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Message]] = []
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    response: str
    model: str
    sources: List[str] = []
    confidence: float = 0.95

class HealthResponse(BaseModel):
    status: str
    mcp_version: str
    model: str

# Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": "Humanoid Robotics MCP Server",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/mcp/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """MCP health check endpoint"""
    return HealthResponse(
        status="healthy",
        mcp_version=MCP_CONFIG["version"],
        model=MCP_CONFIG["model"]["name"]
    )

@app.post("/api/mcp/chat", response_model=ChatResponse, tags=["Chat"])
async def mcp_chat(request: ChatRequest, authorization: Optional[str] = Header(None)):
    """
    MCP-compliant chat endpoint
    
    - **message**: User's message
    - **conversation_history**: Previous conversation context
    - **stream**: Enable streaming response
    """
    
    if not hf_client:
        raise HTTPException(
            status_code=503,
            detail="Hugging Face client not initialized. Set HF_TOKEN environment variable."
        )
    
    # Build messages array
    messages = [
        {"role": "system", "content": MCP_CONFIG["system_prompt"]}
    ]
    
    # Add conversation history
    if request.conversation_history:
        for msg in request.conversation_history[-10:]:  # Last 10 messages
            messages.append({"role": msg.role, "content": msg.content})
    
    # Add current message
    messages.append({"role": "user", "content": request.message})
    
    try:
        # Call Hugging Face Inference API
        response = hf_client.chat_completion(
            model=MCP_CONFIG["model"]["name"],
            messages=messages,
            max_tokens=MCP_CONFIG["model"]["max_tokens"],
            temperature=MCP_CONFIG["model"]["temperature"],
            top_p=MCP_CONFIG["model"]["top_p"]
        )
        
        assistant_message = response.choices[0].message.content
        
        return ChatResponse(
            response=assistant_message,
            model=MCP_CONFIG["model"]["name"],
            sources=[],
            confidence=0.95
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference error: {str(e)}"
        )

@app.post("/api/mcp/embed", tags=["Embeddings"])
async def create_embedding(text: str):
    """Create embeddings using Hugging Face"""
    if not hf_client:
        raise HTTPException(status_code=503, detail="HF client not initialized")
    
    try:
        response = hf_client.feature_extraction(
            text,
            model="sentence-transformers/all-MiniLM-L6-v2"
        )
        return {"embedding": response.tolist(), "dimension": len(response)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")

@app.get("/api/mcp/models", tags=["Models"])
async def list_models():
    """List available MCP models"""
    return {
        "chat": MCP_CONFIG["model"]["name"],
        "embeddings": "sentence-transformers/all-MiniLM-L6-v2",
        "version": MCP_CONFIG["version"]
    }

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🚀 Starting MCP Server on port {port}")
    print(f"📦 Model: {MCP_CONFIG['model']['name']}")
    print(f"🔑 HF Token: {'Set' if HF_TOKEN else 'Not Set'}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

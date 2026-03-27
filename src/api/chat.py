from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from backend.models.question import Question
from backend.models.response import ChatbotResponse
from backend.services.chat.generation import ChatService
from backend.services.rag.retrieval import RAGService
from backend.services.rag.vector_store import VectorStore
from backend.config import QDRANT_URL, QDRANT_API_KEY
from backend.services.chat.validation import ConstitutionValidationService

router = APIRouter()


class QuestionRequest(BaseModel):
    question: str


class StartSessionResponse(BaseModel):
    sessionId: str


class QuestionResponse(BaseModel):
    response: str
    confidence: str
    sources: List[str]


class Message(BaseModel):
    role: str
    content: str
    timestamp: str


class HistoryResponse(BaseModel):
    messages: List[Message]


@router.post("/start", response_model=StartSessionResponse)
async def start_session():
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    # In a real implementation, we would store this session in a database
    return {"sessionId": session_id}


@router.post("/{sessionId}/question", response_model=QuestionResponse)
async def ask_question(sessionId: str, request: QuestionRequest):
    # Initialize services
    vector_store = VectorStore(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    rag_service = RAGService(vector_store=vector_store)
    chat_service = ChatService()
    validation_service = ConstitutionValidationService()

    # Retrieve relevant context from the textbook
    # Using a fixed collection name for now - in production this would be configurable
    retrieved_context = rag_service.retrieve_context(
        query=request.question,
        collection_name="textbook_content"
    )

    # Check if the topic is covered in the book
    if validation_service.is_topic_unavailable_query(request.question, [item['text'] for item in retrieved_context]):
        return QuestionResponse(
            response=validation_service.handle_unavailable_topic(),
            confidence="NONE",
            sources=[]
        )

    # Generate response based on the retrieved context
    response = chat_service.generate_response(request.question, retrieved_context)

    return QuestionResponse(
        response=response.content,
        confidence=response.confidence,
        sources=response.sources
    )


@router.get("/{sessionId}/history", response_model=HistoryResponse)
async def get_conversation_history(sessionId: str):
    # In a real implementation, this would fetch from a database
    # For now, returning an empty list
    return {"messages": []}


@router.post("/{sessionId}/end")
async def end_session(sessionId: str):
    # In a real implementation, this would update the session status in a database
    return {"message": "Session ended"}

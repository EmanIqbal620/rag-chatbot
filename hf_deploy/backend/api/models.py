"""
Pydantic Models for Chat API
"""
from pydantic import BaseModel
from typing import Optional, List, Any


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str
    selected_text: Optional[str] = None


class Source(BaseModel):
    """Source reference from the textbook."""
    chapter_name: str
    source_url: str
    score: float


class ChatData(BaseModel):
    """Response data for chat."""
    answer: str
    sources: List[Source] = []


class APIResponse(BaseModel):
    """API Response envelope."""
    status: str
    data: Optional[ChatData] = None
    error: Optional[str] = None

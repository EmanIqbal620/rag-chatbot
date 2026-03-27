from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ChatbotResponse(BaseModel):
    id: str
    content: str
    questionId: str
    timestamp: datetime
    confidence: str  # HIGH, MEDIUM, LOW, NONE
    sources: List[str]

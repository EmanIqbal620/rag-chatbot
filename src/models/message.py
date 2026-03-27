from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Message(BaseModel):
    id: str
    sessionId: str
    role: str  # USER or ASSISTANT
    content: str
    timestamp: datetime
    questionId: Optional[str] = None
    responseId: Optional[str] = None

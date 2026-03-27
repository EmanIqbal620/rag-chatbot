from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ConversationSession(BaseModel):
    id: str
    userId: Optional[str] = None
    startTime: datetime
    endTime: Optional[datetime] = None
    isActive: bool = True
    messages: List["Message"] = []

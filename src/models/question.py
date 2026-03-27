from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Question(BaseModel):
    id: str
    content: str
    timestamp: datetime
    sessionId: str
    processed: bool = False

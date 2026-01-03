from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class ConversationList(BaseModel):
    conversations: list[ConversationResponse]

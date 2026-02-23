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
    updated_at: datetime
    message_count: int = 0
    last_message_preview: Optional[str] = None

    class Config:
        from_attributes = True

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class ConversationList(BaseModel):
    conversations: list[ConversationResponse]
    total: int = 0
    limit: int = 50
    offset: int = 0

from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatSessionCreate(BaseModel):
    user_id: int
    title: str
    messages: List[ChatMessage] = []

class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    messages: List[ChatMessage]

    class Config:
        from_attributes = True

# class ChatSessionRequest(BaseModel):
#     message: str
#     system_prompt: Optional[str] = "You are an AI customer support assistant."
#     document_ids: Optional[List[int]] = None

class ChatHistoryItem(BaseModel):
    id: int
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    conversation_id: int

    class Config:
        from_attributes = True

class ChatHistoryList(BaseModel):
    history: List[ChatHistoryItem]
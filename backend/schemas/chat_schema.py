from pydantic import BaseModel
from typing import List

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
        orm_mode = True

class ChatHistoryItem(BaseModel):
    id: int
    message: str
    response: str
    timestamp: str

    class Config:
        orm_mode = True

class ChatHistoryList(BaseModel):
    history: List[ChatHistoryItem]
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.conversation import Conversation
from models.document import Document
from models.chat import ChatHistory
from models.user import User

def get_conversation(
        db: Session,
        convo_id: int,
        user: User
) -> Conversation:
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == convo_id)
        .first()
    ) 

    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if convo.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return convo


def check_document_ownership(
        db: Session,
        document_id: int,
        user: User
) -> Document:
    """Check if user owns the document"""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == user.id)
        .first()
    )
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
    
    return doc


def check_chat_ownership(
        db: Session,
        chat_id: int,
        user: User
) -> ChatHistory:
    """Check if user owns the chat"""
    chat = (
        db.query(ChatHistory)
        .filter(ChatHistory.id == chat_id, ChatHistory.user_id == user.id)
        .first()
    )
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    return chat

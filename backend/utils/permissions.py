from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.conversation import Conversation
from models.document import Document
from models.chat import ChatHistory
from models.user import User

async def get_conversation(
        db: AsyncSession,
        convo_id: int,
        user: User
) -> Conversation:
    result = await db.execute(
        select(Conversation).filter(Conversation.id == convo_id)
    )
    convo = result.scalar_one_or_none()

    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if convo.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return convo


async def check_document_ownership(
        db: AsyncSession,
        document_id: int,
        user: User
) -> Document:
    """Check if user owns the document"""
    result = await db.execute(
        select(Document).filter(
            Document.id == document_id,
            Document.owner_id == user.id
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
    
    return doc


async def check_chat_ownership(
        db: AsyncSession,
        chat_id: int,
        user: User
) -> ChatHistory:
    """Check if user owns the chat"""
    result = await db.execute(
        select(ChatHistory).filter(
            ChatHistory.id == chat_id,
            ChatHistory.user_id == user.id
        )
    )
    chat = result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    return chat

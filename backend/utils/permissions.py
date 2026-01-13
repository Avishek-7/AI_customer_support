from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.conversation import Conversation
from models.document import Document
from models.chat import ChatHistory
from models.user import User
from core.error_handler import ErrorHandler

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
        raise ErrorHandler.not_found("Conversation not found")
    
    if convo.user_id != user.id:
        raise ErrorHandler.forbidden("You do not have permission to access this conversation")
    
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
        raise ErrorHandler.not_found("Document not found or you do not have access to it")
    
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
        raise ErrorHandler.not_found("Chat not found or you do not have access to it")
    
    return chat

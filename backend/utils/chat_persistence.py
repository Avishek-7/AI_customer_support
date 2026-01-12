from typing import Tuple, Optional
from models.chat import ChatHistory
from utils.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("backend.utils.chat_persistence")


async def save_chat_turn(
    db: AsyncSession,
    user_id: int,
    conversation_id: int,
    user_message: str,
    assistant_response: str,
) -> tuple[ChatHistory, ChatHistory] | None:
    """
    Save a complete chat turn (user message + assistant response) to the database.
    
    Args:
        db: Async database session
        user_id: ID of the user
        conversation_id: ID of the conversation
        user_message: The user's message
        assistant_response: The assistant's response
    
    Returns:
        Tuple of (user_chat, assistant_chat) records if saved successfully,
        None if assistant response is empty (streaming edge case)
    
    Raises:
        Exception: Re-raises after rollback for caller to handle
    """
    # Guard against empty responses (can happen with streaming errors)
    if not assistant_response or not assistant_response.strip():
        logger.warning("Empty assistant response, skipping save", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
        })
        return None
    
    try:
        user_chat = ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )
        assistant_chat = ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_response,
        )
        
        db.add(user_chat)
        db.add(assistant_chat)
        await db.commit()
        
        # Refresh to get generated IDs
        await db.refresh(user_chat)
        await db.refresh(assistant_chat)
        
        logger.info("Chat turn saved", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_chat_id": user_chat.id,
            "assistant_chat_id": assistant_chat.id,
            "user_msg_len": len(user_message),
            "assistant_msg_len": len(assistant_response),
        })
        
        return (user_chat, assistant_chat)
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to save chat turn", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "error": str(e),
        })
        raise
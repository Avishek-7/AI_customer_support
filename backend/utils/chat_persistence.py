from typing import Tuple, Optional
from models.chat import ChatHistory
from models.conversation import Conversation
from utils.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

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
    
    This function ensures:
    - Atomic transaction handling (both messages saved together or none)
    - Rollback protection (all DB changes rolled back on failure)
    - Conversation title updated on first message (only once)
    
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
        # Verify conversation exists and belongs to user
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found or access denied for user {user_id}")

        # Use naive datetime to match database TIMESTAMP WITHOUT TIME ZONE columns
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        
        user_chat = ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            timestamp=timestamp,
            created_at=timestamp
        )
        assistant_chat = ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_response,
            timestamp=timestamp,
            created_at=timestamp
        )
        
        db.add(user_chat)
        db.add(assistant_chat)
        
        # Update conversation title on first message (only once - don't override user edits)
        if conversation.title == "New Conversation":
            conversation.title = user_message[:40] + ("..." if len(user_message) > 40 else "")
            conversation.updated_at = timestamp
        
        await db.commit()
        
        # Refresh to get generated IDs
        await db.refresh(user_chat)
        await db.refresh(assistant_chat)
        
        logger.info("Chat turn saved successfully", extra={
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
        logger.error("Failed to save chat turn (rolled back)", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "error": str(e),
            "error_type": type(e).__name__,
        })
        raise
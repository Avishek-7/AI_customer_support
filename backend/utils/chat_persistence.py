from models.chat import ChatHistory
from utils.logger import get_logger

logger = get_logger("backend.utils.chat_persistence")


async def save_chat_turn(
    db,
    user_id: int,
    conversation_id: int,
    user_message: str,
    assistant_response: str,
) -> bool:
    """
    Save a complete chat turn (user message + assistant response) to the database.
    
    Handles:
    - Adding user message
    - Adding assistant response  
    - Committing transaction
    - Rolling back on failure
    
    Returns:
        True if saved successfully, False otherwise
    
    Raises:
        Exception: Re-raises after rollback for caller to handle
    """
    try:
        db.add(ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        ))
        db.add(ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_response,
        ))
        await db.commit()
        
        logger.info("Chat turn saved", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_msg_len": len(user_message),
            "assistant_msg_len": len(assistant_response),
        })
        return True
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to save chat turn", extra={
            "user_id": user_id,
            "conversation_id": conversation_id,
            "error": str(e),
        })
        raise
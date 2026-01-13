from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import time
from core.database import get_db
from core.security import get_current_user
from core.config import settings
from core.rate_limit import rate_limit
from core.error_handler import ErrorHandler
from utils.usage_tracker import track_usage
from models.user import User
from models.document import Document
from models.chat import ChatHistory
from models.conversation import Conversation
from schemas.chat_schema import ChatHistoryList, ChatHistoryItem
from schemas.conversation_schema import ConversationCreate, ConversationResponse, ConversationList, ConversationUpdate
from utils.logger import get_logger
from utils.chat_persistence import save_chat_turn

logger = get_logger("backend.api.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

AI_ENGINE_URL = settings.AI_ENGINE_URL


# Helper function to enrich conversation with metadata
async def enrich_conversation_response(
    db: AsyncSession,
    conversation: Conversation
) -> ConversationResponse:
    """Enrich a conversation with metadata (message count, last preview, etc)"""
    # Get message count
    message_count_result = await db.execute(
        select(func.count(ChatHistory.id)).filter(
            ChatHistory.conversation_id == conversation.id
        )
    )
    message_count = message_count_result.scalar() or 0
    
    # Get last message (assistant response) for preview
    last_msg_result = await db.execute(
        select(ChatHistory)
        .filter(
            ChatHistory.conversation_id == conversation.id,
            ChatHistory.role == "assistant"
        )
        .order_by(ChatHistory.timestamp.desc())
        .limit(1)
    )
    last_message = last_msg_result.scalar_one_or_none()
    last_preview = None
    
    if last_message:
        # Truncate to first 100 chars for preview
        last_preview = last_message.content[:100] + ("..." if len(last_message.content) > 100 else "")
    
    return ConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
        last_message_preview=last_preview
    )


# Request and Response Models
class ChatRequest(BaseModel):
    message: str
    conversation_id: int  # Required: conversations must be created explicitly
    system_prompt: Optional[str] = "You are an AI customer support assistant."
    document_ids: Optional[List[int]] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]

# Chat Endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Main Chat Endpoint.
    Requires an explicit conversation_id.
    1. Verify conversation exists and belongs to user
    2. Find all documents of the user
    3. Send query + doc_ids to AI Engine /query
    4. Save to conversation
    5. Return answer + citations
    """
    # Rate limiting check
    rate_limit(current_user.id, limit=100, window=60)
    
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == body.conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        logger.warning(f"Chat request for non-existent conversation", extra={
            "user_id": current_user.id,
            "conversation_id": body.conversation_id
        })
        raise ErrorHandler.not_found("Conversation not found. Please create a conversation first.")
    
    # Start timer for latency tracking
    start_time = time.time()
    
    logger.info(f"Chat request received", extra={
        "user_id": current_user.id,
        "conversation_id": body.conversation_id,
        "message_length": len(body.message),
        "document_ids": body.document_ids
    })
    
    # Only filter by document_ids if user explicitly selected specific documents
    if body.document_ids and len(body.document_ids) > 0:
        result = await db.execute(
            select(Document).filter(
                Document.owner_id == current_user.id,
                Document.id.in_(body.document_ids)
            )
        )
        user_docs = result.scalars().all()
        document_ids = [doc.id for doc in user_docs]
    else:
        # No selection - search ALL documents in FAISS (pass None)
        document_ids = None

    logger.info(f"Querying AI engine", extra={"document_count": len(document_ids) if document_ids else "ALL"})

    # Call AI Engine
    async with httpx.AsyncClient() as client:
        try:
            ai_response = await client.post(
                f"{AI_ENGINE_URL}/query",
                json={
                    "query": body.message,
                    "system_prompt": body.system_prompt,
                    "document_ids": document_ids,  # None means search all
                    "k": 5,
                },
                timeout=40.0,
            )
            ai_response.raise_for_status()
        except httpx.TimeoutException:
            logger.error(f"AI engine timeout", extra={
                "user_id": current_user.id,
                "conversation_id": body.conversation_id
            })
            raise ErrorHandler.service_unavailable("AI engine is taking too long. Please try again.")
        except httpx.HTTPError as e:
            logger.error(f"AI engine error", extra={
                "error": str(e),
                "user_id": current_user.id,
                "conversation_id": body.conversation_id
            })
            raise ErrorHandler.service_unavailable("AI engine is unavailable. Please try again later.")
    
    data = ai_response.json()
    
    # Log the full answer received from AI engine for debugging/comparison
    logger.info("=== BACKEND RECEIVED ANSWER ===", extra={
        "user_id": current_user.id,
        "query": body.message,
        "answer": data["answer"],
        "answer_length": len(data["answer"]),
        "sources_count": len(data["sources"])
    })

    try:
        await save_chat_turn(
            db,
            current_user.id,
            body.conversation_id,
            body.message,
            data["answer"]
        )
    except Exception as e:
        logger.error(f"Failed to persist chat history", extra={
            "user_id": current_user.id,
            "conversation_id": body.conversation_id,
            "error": str(e)
        })
        # Log the error but still return the answer to the user
        # (chat persistence failure shouldn't break the response)

    # Track API usage
    latency = time.time() - start_time
    tokens = len(data["answer"].split())  # Approximate token count
    try:
        await track_usage(db, current_user.id, "/chat", tokens, latency)
    except Exception as e:
        logger.error(f"Failed to track usage", extra={
            "user_id": current_user.id,
            "error": str(e)
        })
        # Don't break response if tracking fails

    # Return formatted answer to frontend
    return ChatResponse(
        answer=data["answer"],
        sources=data["sources"]
    )

@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Streaming chat endpoint.
    Requires an explicit conversation_id.
    """
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == body.conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        logger.warning(f"Stream request for non-existent conversation", extra={
            "user_id": current_user.id,
            "conversation_id": body.conversation_id
        })
        raise ErrorHandler.not_found("Conversation not found. Please create a conversation first.")
    
    # Start timer for latency tracking
    start_time = time.time()
    
    logger.info(f"Stream chat request", extra={
        "user_id": current_user.id,
        "conversation_id": body.conversation_id,
        "message_length": len(body.message),
        "document_ids": body.document_ids
    })
    
    # Only filter by document_ids if user explicitly selected specific documents
    # If no selection, pass None to search ALL indexed documents in FAISS
    if body.document_ids and len(body.document_ids) > 0:
        # Validate that user owns these documents
        result = await db.execute(
            select(Document).filter(
                Document.owner_id == current_user.id,
                Document.id.in_(body.document_ids)
            )
        )
        docs = result.scalars().all()
        document_ids = [d.id for d in docs]
        user_selected_docs = True
    else:
        # No selection - search ALL documents in FAISS (pass None)
        document_ids = None
        user_selected_docs = False
    
    logger.info(f"Streaming from AI engine", extra={
        "document_count": len(document_ids) if document_ids else "ALL",
        "document_ids": document_ids,
        "selected_by_user": user_selected_docs
    })

    # Shared list to collect answer tokens
    full_answer_tokens = []

    # SSE generator
    async def event_generator():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{AI_ENGINE_URL}/stream",
                    json={
                        "query": body.message,
                        "session_id": str(current_user.id),
                        "system_prompt": body.system_prompt,
                        "document_ids": document_ids,  # None means search all
                    },
                    timeout=None,
                ) as stream:
                    async for chunk in stream.aiter_lines():
                        if chunk.strip():
                            # Track tokens for logging
                            if chunk.startswith("data: "):
                                try:
                                    data = json.loads(chunk[6:])
                                    if data.get("type") == "token":
                                        full_answer_tokens.append(data.get("content", ""))
                                except:
                                    pass
                            # Pass through as-is; AI engine already formats as "data: {...}"
                            yield chunk + "\n\n"
            except httpx.TimeoutException:
                logger.error(f"AI engine stream timeout", extra={
                    "user_id": current_user.id,
                    "conversation_id": body.conversation_id
                })
                yield "data: {\"type\": \"error\", \"message\": \"AI engine is taking too long\"}\n\n"
            except httpx.HTTPError as e:
                logger.error(f"AI engine stream error", extra={
                    "error": str(e),
                    "user_id": current_user.id,
                    "conversation_id": body.conversation_id
                })
                yield "data: {\"type\": \"error\", \"message\": \"AI engine error\"}\n\n"
        
        # Log the complete streamed answer received from AI engine
        full_answer = "".join(full_answer_tokens)
        logger.info("Stream completed", extra={
            "user_id": current_user.id,
            "query": body.message,
            "answer_length": len(full_answer),
            "token_count": len(full_answer_tokens)
        })
    
    response = StreamingResponse(event_generator(), media_type="text/event-stream")

    async def background_save():
        """Save chat history after streaming completes"""
        if not full_answer_tokens:
            full_answer = ""
        else:
            full_answer = "".join(full_answer_tokens)
        
        try:
            await save_chat_turn(
                db,
                current_user.id,
                body.conversation_id,
                body.message,
                full_answer
            )
        except Exception as e:
            logger.error(f"Failed to persist streamed chat history", extra={
                "user_id": current_user.id,
                "conversation_id": body.conversation_id,
                "error": str(e)
            })
        
        # Track API usage
        latency = time.time() - start_time
        tokens = len(full_answer_tokens)
        try:
            await track_usage(db, current_user.id, "/chat/stream", tokens, latency)
        except Exception as e:
            logger.error(f"Failed to track stream usage", extra={
                "user_id": current_user.id,
                "error": str(e)
            })
    
    background_tasks.add_task(background_save)
    return response


# Conversation Management Endpoints

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    body: ConversationCreate = ConversationCreate(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new conversation explicitly.
    Conversations must be created before chat messages can be added to them.
    """
    start_time = time.time()
    
    logger.info(f"Creating new conversation", extra={
        "user_id": current_user.id,
        "title": body.title
    })
    
    conversation = Conversation(
        user_id=current_user.id,
        title=body.title or "New Conversation"
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    latency = time.time() - start_time
    logger.info(f"Conversation created", extra={
        "user_id": current_user.id,
        "conversation_id": conversation.id,
        "title": conversation.title,
        "latency": f"{latency:.3f}s"
    })
    
    return await enrich_conversation_response(db, conversation)


@router.get("/conversations", response_model=ConversationList)
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all conversations for the current user with metadata.
    Includes: message count, last message preview, updated timestamp.
    """
    start_time = time.time()
    
    logger.info(f"Fetching conversations", extra={"user_id": current_user.id})
    
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    
    # Enrich each conversation with metadata
    enriched_conversations = []
    for conv in conversations:
        enriched = await enrich_conversation_response(db, conv)
        enriched_conversations.append(enriched)
    
    latency = time.time() - start_time
    logger.info(f"Conversations retrieved", extra={
        "user_id": current_user.id,
        "count": len(conversations),
        "latency": f"{latency:.3f}s"
    })
    
    return ConversationList(conversations=enriched_conversations)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific conversation by ID with metadata.
    """
    start_time = time.time()
    
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        logger.warning(f"Conversation not found", extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id
        })
        raise ErrorHandler.not_found("Conversation not found")
    
    latency = time.time() - start_time
    logger.info(f"Conversation retrieved", extra={
        "user_id": current_user.id,
        "conversation_id": conversation_id,
        "title": conversation.title,
        "latency": f"{latency:.3f}s"
    })
    
    return await enrich_conversation_response(db, conversation)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    body: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a conversation (e.g., rename title).
    """
    start_time = time.time()
    
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        logger.warning(f"Conversation not found for update", extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id
        })
        raise ErrorHandler.not_found("Conversation not found")
    
    if body.title is not None:
        conversation.title = body.title
    
    await db.commit()
    await db.refresh(conversation)
    
    latency = time.time() - start_time
    logger.info(f"Conversation updated", extra={
        "user_id": current_user.id,
        "conversation_id": conversation_id,
        "new_title": conversation.title,
        "latency": f"{latency:.3f}s"
    })
    
    return await enrich_conversation_response(db, conversation)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation and all its messages.
    """
    start_time = time.time()
    
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        logger.warning(f"Conversation not found for deletion", extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id
        })
        raise ErrorHandler.not_found("Conversation not found")
    
    try:
        await db.delete(conversation)
        await db.commit()
        
        latency = time.time() - start_time
        logger.info(f"Conversation deleted", extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id,
            "latency": f"{latency:.3f}s"
        })
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete conversation", extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id,
            "error": str(e)
        })
        raise ErrorHandler.internal_error("Failed to delete conversation")
    
    return {"message": "Conversation deleted successfully"}


@router.get("/conversations/{conversation_id}/messages", response_model=ChatHistoryList)
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all messages in a specific conversation.
    """
    start_time = time.time()
    
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        logger.warning(f"Conversation not found for messages", extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id
        })
        raise ErrorHandler.not_found("Conversation not found")
    
    # Get messages
    result = await db.execute(
        select(ChatHistory)
        .filter(ChatHistory.conversation_id == conversation_id)
        .order_by(ChatHistory.timestamp.asc())
    )
    messages = result.scalars().all()
    
    latency = time.time() - start_time
    logger.info(f"Conversation messages retrieved", extra={
        "user_id": current_user.id,
        "conversation_id": conversation_id,
        "message_count": len(messages),
        "latency": f"{latency:.3f}s"
    })
    
    return ChatHistoryList(history=messages)


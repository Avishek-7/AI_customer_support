from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import httpx
import json
import time
from core.database import get_db
from core.database import AsyncSessionLocal
from core.security import get_current_user
from core.config import settings
from core.rate_limit import rate_limit
from core.error_handler import ErrorHandler
from utils.usage_tracker import track_usage, count_tokens
from utils.cache import get_cached_response, set_cached_response
from utils.metrics import AI_ENGINE_LATENCY, CACHE_HITS, CACHE_MISSES
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


async def enrich_conversation_list_response(
    db: AsyncSession,
    conversations: List[Conversation],
) -> List[ConversationResponse]:
    if not conversations:
        return []

    conversation_ids = [c.id for c in conversations]

    message_count_result = await db.execute(
        select(ChatHistory.conversation_id, func.count(ChatHistory.id))
        .filter(ChatHistory.conversation_id.in_(conversation_ids))
        .group_by(ChatHistory.conversation_id)
    )
    message_count_map = {conv_id: count for conv_id, count in message_count_result.all()}

    assistant_preview_result = await db.execute(
        select(ChatHistory.conversation_id, ChatHistory.content)
        .filter(
            ChatHistory.conversation_id.in_(conversation_ids),
            ChatHistory.role == "assistant",
        )
        .order_by(ChatHistory.conversation_id.asc(), ChatHistory.timestamp.desc())
    )

    preview_map = {}
    for conversation_id, content in assistant_preview_result.all():
        if conversation_id not in preview_map:
            preview_map[conversation_id] = content[:100] + ("..." if len(content) > 100 else "")

    return [
        ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=message_count_map.get(conversation.id, 0),
            last_message_preview=preview_map.get(conversation.id),
        )
        for conversation in conversations
    ]


async def _save_chat_turn_with_retry(
    db: AsyncSession,
    user_id: int,
    conversation_id: int,
    user_message: str,
    assistant_response: str,
    retries: int = 3,
) -> None:
    for attempt in range(1, retries + 1):
        try:
            await save_chat_turn(
                db,
                user_id,
                conversation_id,
                user_message,
                assistant_response,
            )
            return
        except Exception:
            if attempt == retries:
                raise
            await asyncio.sleep(0.1 * (2 ** (attempt - 1)))


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
@router.post("", response_model=ChatResponse)
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

    try:
        cached = await get_cached_response(
            user_id=current_user.id,
            conversation_id=body.conversation_id,
            message=body.message,
            system_prompt=body.system_prompt,
            document_ids=document_ids,
        )
    except Exception as e:
        logger.warning("Cache lookup failed, proceeding without cache", extra={
            "user_id": current_user.id,
            "error": str(e)
        })
        cached = None
    if cached:
        CACHE_HITS.labels("/chat").inc()
        logger.info("Chat cache hit", extra={
            "user_id": current_user.id,
            "conversation_id": body.conversation_id
        })
        data = cached
    else:
        CACHE_MISSES.labels("/chat").inc()
        # Call AI Engine
        ai_start = time.perf_counter()
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
        ai_duration = time.perf_counter() - ai_start
        AI_ENGINE_LATENCY.labels("/query").observe(ai_duration)

        data = ai_response.json()
        await set_cached_response(
            user_id=current_user.id,
            conversation_id=body.conversation_id,
            message=body.message,
            system_prompt=body.system_prompt,
            document_ids=document_ids,
            response=data,
        )
    
    # Log the full answer received from AI engine for debugging/comparison
    logger.info("=== BACKEND RECEIVED ANSWER ===", extra={
        "user_id": current_user.id,
        "query": body.message,
        "answer": data["answer"],
        "answer_length": len(data["answer"]),
        "sources_count": len(data["sources"])
    })

    try:
        await _save_chat_turn_with_retry(
            db,
            current_user.id,
            body.conversation_id,
            body.message,
            data["answer"],
        )
    except Exception as e:
        logger.error(f"Failed to persist chat history", extra={
            "user_id": current_user.id,
            "conversation_id": body.conversation_id,
            "error": str(e)
        }, exc_info=True)
        raise ErrorHandler.internal_error("Failed to persist chat response")

    # Track API usage
    latency = time.time() - start_time
    tokens = count_tokens(data["answer"])
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Streaming chat endpoint.
    Requires an explicit conversation_id.
    """
    # Rate limiting check (same as non-stream endpoint)
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
        local_db = AsyncSessionLocal()
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
                    timeout=httpx.Timeout(300.0, connect=10.0, read=300.0, write=30.0),
                ) as stream:
                    async for chunk in stream.aiter_lines():
                        if chunk.strip():
                            # Track tokens for logging
                            if chunk.startswith("data: "):
                                try:
                                    data = json.loads(chunk[6:])
                                    if data.get("type") == "token":
                                        full_answer_tokens.append(data.get("content", ""))
                                except json.JSONDecodeError as e:
                                    logger.debug("Skipping non-JSON stream chunk", extra={
                                        "conversation_id": body.conversation_id,
                                        "error": str(e),
                                        "chunk_preview": chunk[:120],
                                    })
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
        
        full_answer = "".join(full_answer_tokens)
        logger.info("Stream completed", extra={
            "user_id": current_user.id,
            "query": body.message,
            "answer_length": len(full_answer),
            "token_count": len(full_answer_tokens)
        })

        try:
            await _save_chat_turn_with_retry(
                local_db,
                current_user.id,
                body.conversation_id,
                body.message,
                full_answer,
            )
        except Exception as e:
            logger.error("Failed to persist streamed chat history", extra={
                "user_id": current_user.id,
                "conversation_id": body.conversation_id,
                "error": str(e),
            }, exc_info=True)
            yield "data: {\"type\": \"error\", \"message\": \"Failed to persist chat response\"}\n\n"

        latency = time.time() - start_time
        tokens = count_tokens(full_answer)
        try:
            await track_usage(local_db, current_user.id, "/chat/stream", tokens, latency)
        except Exception as e:
            logger.error(f"Failed to track stream usage", extra={
                "user_id": current_user.id,
                "error": str(e)
            })
        finally:
            await local_db.close()
    
    response = StreamingResponse(event_generator(), media_type="text/event-stream")

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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
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
        .offset(offset)
        .limit(limit)
    )
    conversations = result.scalars().all()

    total_result = await db.execute(
        select(func.count(Conversation.id)).filter(Conversation.user_id == current_user.id)
    )
    total = total_result.scalar() or 0
    
    enriched_conversations = await enrich_conversation_list_response(db, conversations)
    
    latency = time.time() - start_time
    logger.info(f"Conversations retrieved", extra={
        "user_id": current_user.id,
        "count": len(conversations),
        "latency": f"{latency:.3f}s"
    })
    
    return ConversationList(conversations=enriched_conversations, total=total, limit=limit, offset=offset)


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
    
    # Convert to schema format
    history_items = [
        ChatHistoryItem(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp.isoformat() if msg.timestamp else "",
            conversation_id=msg.conversation_id
        )
        for msg in messages
    ]
    
    latency = time.time() - start_time
    logger.info(f"Conversation messages retrieved", extra={
        "user_id": current_user.id,
        "conversation_id": conversation_id,
        "message_count": len(messages),
        "latency": f"{latency:.3f}s"
    })
    
    return ChatHistoryList(history=history_items)


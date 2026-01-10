from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import time
from core.database import get_db
from core.security import get_current_user
from core.config import settings
from core.rate_limit import rate_limit
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
        raise HTTPException(
            status_code=404,
            detail="Conversation not found. Please create a conversation first."
        )
    
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
        except Exception as e:
            logger.error(f"AI engine error", extra={"error": str(e)})
            raise HTTPException(
                status_code=500,
                detail="AI engine is unavailable. Please try again later."
            )
    
    data = ai_response.json()
    
    # Log the full answer received from AI engine for debugging/comparison
    logger.info("=== BACKEND RECEIVED ANSWER ===", extra={
        "user_id": current_user.id,
        "query": body.message,
        "answer": data["answer"],
        "answer_length": len(data["answer"]),
        "sources_count": len(data["sources"])
    })
    logger.info(f"[BACKEND_RECEIVED] {data['answer'][:500]}..." if len(data["answer"]) > 500 else f"[BACKEND_RECEIVED] {data['answer']}")

    await save_chat_turn(
        db,
        current_user.id,
        body.conversation_id,
        body.message,
        data["answer"]
    )

    # Update conversation title on first message
    if conversation.title == "New Conversation":
        conversation.title = body.message[:40] + "..."
        await db.commit()

    # Track API usage
    latency = time.time() - start_time
    tokens = len(data["answer"].split())  # Approximate token count
    await track_usage(db, current_user.id, "/chat", tokens, latency)

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
        raise HTTPException(
            status_code=404,
            detail="Conversation not found. Please create a conversation first."
        )
    
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
        
        # Log the complete streamed answer received from AI engine
        full_answer = "".join(full_answer_tokens)
        logger.info("=== BACKEND STREAM RECEIVED ===", extra={
            "user_id": current_user.id,
            "query": body.message,
            "answer": full_answer,
            "answer_length": len(full_answer),
            "token_count": len(full_answer_tokens)
        })
        logger.info(f"[BACKEND_STREAM_RECEIVED] {full_answer[:500]}..." if len(full_answer) > 500 else f"[BACKEND_STREAM_RECEIVED] {full_answer}")
    
    response = StreamingResponse(event_generator(), media_type="text/event-stream")

    async def background_save():
        """Save chat history after streaming completes"""
        if not full_answer_tokens:
            full_answer = ""
        else:
            full_answer = "".join(full_answer_tokens)
        
        await save_chat_turn(
            db,
            current_user.id,
            body.conversation_id,
            body.message,
            full_answer
        )

        # Update conversation title on first message
        if conversation.title == "New Conversation":
            conversation.title = body.message[:40] + "..."
            await db.commit()
        
        # Track API usage
        latency = time.time() - start_time
        tokens = len(full_answer_tokens)
        await track_usage(db, current_user.id, "/chat/stream", tokens, latency)
    
    background_tasks.add_task(background_save)
    return response


# Get past chats (legacy - use /conversations/{id}/messages instead)
@router.get("/history", response_model=ChatHistoryList)
async def get_chat_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Fetching chat history", extra={"user_id": current_user.id})
    result = await db.execute(
        select(ChatHistory)
        .filter(ChatHistory.user_id == current_user.id)
        .order_by(ChatHistory.id.desc())
    )
    chats = result.scalars().all()
    logger.info(f"Chat history retrieved", extra={"user_id": current_user.id, "count": len(chats)})
    return ChatHistoryList(history=chats)


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
    
    logger.info(f"Conversation created", extra={
        "user_id": current_user.id,
        "conversation_id": conversation.id,
        "title": conversation.title
    })
    
    return conversation


@router.get("/conversations", response_model=ConversationList)
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all conversations for the current user.
    """
    logger.info(f"Fetching conversations", extra={"user_id": current_user.id})
    
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    
    logger.info(f"Conversations retrieved", extra={
        "user_id": current_user.id,
        "count": len(conversations)
    })
    
    return ConversationList(conversations=conversations)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific conversation by ID.
    """
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


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
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if body.title is not None:
        conversation.title = body.title
    
    await db.commit()
    await db.refresh(conversation)
    
    logger.info(f"Conversation updated", extra={
        "user_id": current_user.id,
        "conversation_id": conversation_id,
        "new_title": conversation.title
    })
    
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation and all its messages.
    """
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conversation)
    await db.commit()
    
    logger.info(f"Conversation deleted", extra={
        "user_id": current_user.id,
        "conversation_id": conversation_id
    })
    
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
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    result = await db.execute(
        select(ChatHistory)
        .filter(ChatHistory.conversation_id == conversation_id)
        .order_by(ChatHistory.timestamp.asc())
    )
    messages = result.scalars().all()
    
    logger.info(f"Conversation messages retrieved", extra={
        "user_id": current_user.id,
        "conversation_id": conversation_id,
        "message_count": len(messages)
    })
    
    return ChatHistoryList(history=messages)


from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import httpx
import time
from core.database import get_db
from core.security import get_current_user
from core.config import settings
from core.rate_limit import rate_limit
from utils.usage_tracker import track_usage
from models.user import User
from models.document import Document
from models.chat import ChatHistory
from schemas.chat_schema import ChatHistoryList, ChatHistoryItem
from utils.logger import get_logger

logger = get_logger("backend.api.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

AI_ENGINE_URL = settings.AI_ENGINE_URL

# Request and Response Models
class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = "You are an AI customer support assistant."
    document_ids: Optional[List[int]] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]

# Chat Endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Main Chat Endpoint.
    1. Find all documents of the user
    2. Send query + doc_ids to AI Engine /query
    3. Return answer + citations
    """
    # Rate limiting check
    rate_limit(current_user.id, limit=100, window=60)
    
    # Start timer for latency tracking
    start_time = time.time()
    
    logger.info(f"Chat request received", extra={
        "user_id": current_user.id,
        "message_length": len(body.message),
        "document_ids": body.document_ids
    })
    
    # Only filter by document_ids if user explicitly selected specific documents
    if body.document_ids and len(body.document_ids) > 0:
        user_docs = (
            db.query(Document)
            .filter(
                Document.owner_id == current_user.id,
                Document.id.in_(body.document_ids)
            )
            .all()
        )
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

    # Track API usage
    latency = time.time() - start_time
    tokens = len(data["answer"].split())  # Approximate token count
    track_usage(db, current_user.id, "/chat", tokens, latency)

    # Return formatted answer to frontend
    return ChatResponse(
        answer=data["answer"],
        sources=data["sources"]
    )

@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Start timer for latency tracking
    start_time = time.time()
    
    logger.info(f"Stream chat request", extra={
        "user_id": current_user.id,
        "message_length": len(body.message),
        "document_ids": body.document_ids
    })
    
    # Only filter by document_ids if user explicitly selected specific documents
    # If no selection, pass None to search ALL indexed documents in FAISS
    if body.document_ids and len(body.document_ids) > 0:
        # Validate that user owns these documents
        docs = db.query(Document).filter(
            Document.owner_id == current_user.id,
            Document.id.in_(body.document_ids)
        ).all()
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

    # SSE generator
    async def event_generator():
        full_answer_tokens = []
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
                                import json
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
        
        # Track API usage
        latency = time.time() - start_time
        tokens = len(full_answer_tokens)
        track_usage(db, current_user.id, "/chat/stream", tokens, latency)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Save chat after normal or streaming response
def save_chat_to_db(user_id: int, question: str, answer: str, db: Session):
    history = ChatHistory(
        user_id=user_id,
        message=question,
        response=answer,
    )
    db.add(history)
    db.commit()

# Get past chats
@router.get("/history", response_model=ChatHistoryList)
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Fetching chat history", extra={"user_id": current_user.id})
    chats = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == current_user.id)
        .order_by(ChatHistory.id.desc())
        .all()
    )
    logger.info(f"Chat history retrieved", extra={"user_id": current_user.id, "count": len(chats)})
    return ChatHistoryList(history=chats)

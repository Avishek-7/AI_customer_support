from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
import httpx
import json
import time
from core.database import get_db
from core.roles import require_admin
from core.config import settings
from models.user import User
from models.document import Document
from models.chat import ChatHistory
from models.usage import APIUsage
from models.conversation import Conversation
from models.investigation_audit import InvestigationAudit
from pydantic import BaseModel, Field
from utils.logger import get_logger

logger = get_logger("backend.api.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

AI_ENGINE_URL = settings.AI_ENGINE_URL


# Response Models
class UserStats(BaseModel):
    id: int
    name: Optional[str] = None
    email: str
    role: str
    document_count: int
    chat_count: int
    total_api_calls: int
    
    class Config:
        from_attributes = True


class UsageStats(BaseModel):
    endpoint: str
    total_calls: int
    total_tokens: int
    avg_latency: float


class SystemStats(BaseModel):
    total_users: int
    total_documents: int
    total_chats: int
    total_api_calls: int


class InvestigationRunRequest(BaseModel):
    conversation_id: int
    instruction_intent: Literal[
        "investigate_root_cause",
        "explain_low_confidence",
        "draft_improved_answer",
        "recommend_next_action",
    ] = "investigate_root_cause"
    constraints: Optional[str] = None
    k: int = 5


class InvestigationEvidence(BaseModel):
    retrieved_chunks: List[Dict[str, Any]]
    total_chunks_retrieved: int
    document_ids: List[int]


class InvestigationQualitySummary(BaseModel):
    confidence_score: Optional[float] = None
    hallucination_score: Optional[float] = None
    alignment_score: Optional[float] = None


class InvestigationRunResponse(BaseModel):
    investigation_id: int
    conversation_id: int
    instruction_intent: str
    diagnosis: str
    supporting_evidence: InvestigationEvidence
    quality_summary: InvestigationQualitySummary
    recommended_next_actions: List[str]
    improved_draft_answer: Optional[str] = None
    error_details: List[Dict[str, Any]] = Field(default_factory=list)
    status: str
    created_at: datetime


def _build_upstream_error(response: httpx.Response, context: str) -> Dict[str, Any]:
    response_body: Any
    try:
        response_body = response.json()
    except ValueError:
        response_body = response.text[:500] if response.text else response.reason_phrase

    return {
        "context": context,
        "status_code": response.status_code,
        "body": response_body,
    }


def _derive_diagnosis(
    intent: str,
    quality: InvestigationQualitySummary,
    chunks_retrieved: int,
) -> str:
    confidence = quality.confidence_score
    hallucination = quality.hallucination_score
    alignment = quality.alignment_score

    if intent == "explain_low_confidence":
        return (
            f"Confidence is low at {confidence if confidence is not None else 'N/A'}, "
            f"with {chunks_retrieved} chunks retrieved. "
            "Likely causes are sparse retrieval coverage or weak source grounding."
        )

    if hallucination is not None and hallucination >= 0.6:
        return (
            f"High hallucination risk detected ({hallucination:.2f}) with alignment "
            f"{alignment if alignment is not None else 'N/A'}."
        )

    if chunks_retrieved == 0:
        return "No supporting chunks were retrieved, indicating a retrieval gap for this query."

    return "Investigation completed with available retrieval and critique evidence."


def _derive_recommended_actions(
    intent: str,
    quality: InvestigationQualitySummary,
    chunks_retrieved: int,
) -> List[str]:
    actions = ["Review top retrieved chunks for relevance and freshness."]

    if chunks_retrieved < 2:
        actions.append("Re-index or expand source documents for this topic.")

    if quality.hallucination_score is not None and quality.hallucination_score >= 0.6:
        actions.append("Escalate to human review due to high hallucination risk.")

    if quality.confidence_score is not None and quality.confidence_score < 0.5:
        actions.append("Use narrower document filters and regenerate with explicit constraints.")

    if intent == "recommend_next_action" and len(actions) < 3:
        actions.append("Capture this case as a benchmark failure example for future evaluation.")

    return actions


async def _call_ai_engine_for_investigation(
    query_text: str,
    assistant_answer: Optional[str],
    request: InvestigationRunRequest,
) -> tuple[Dict[str, Any], Dict[str, Any], Optional[str], str, List[str], List[Dict[str, Any]]]:
    headers = {"X-Internal-API-Key": settings.INTERNAL_API_KEY}
    tools_called = ["debug/search-preview", "critique"]
    status = "completed"
    improved_draft_answer: Optional[str] = None
    errors: List[Dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        search_response = await client.get(
            f"{AI_ENGINE_URL}/debug/search-preview",
            params={"query": query_text, "k": request.k},
            headers=headers,
            timeout=30.0,
        )
        if search_response.status_code == 200:
            search_data = search_response.json()
        else:
            status = "failed"
            search_data = {"error": _build_upstream_error(search_response, "debug/search-preview")}
            errors.append(search_data["error"])
            logger.error("AI engine search preview failed", extra=search_data["error"])

        critique_data: Dict[str, Any] = {}
        if assistant_answer and search_data.get("chunks"):
            critique_response = await client.post(
                f"{AI_ENGINE_URL}/critique",
                json={
                    "question": query_text,
                    "answer": assistant_answer,
                    "sources": search_data.get("chunks", []),
                },
                headers=headers,
                timeout=30.0,
            )
            if critique_response.status_code == 200:
                critique_data = critique_response.json()
            else:
                status = "failed"
                critique_data = {"error": _build_upstream_error(critique_response, "critique")}
                errors.append(critique_data["error"])
                logger.error("AI engine critique failed", extra=critique_data["error"])
        if request.instruction_intent == "draft_improved_answer" and assistant_answer:
            safe_constraints = (request.constraints or "Improve clarity and grounding.").strip()[:300]
            regenerate_response = await client.post(
                f"{AI_ENGINE_URL}/regenerate",
                json={
                    "session_id": f"investigation-{request.conversation_id}",
                    "query": query_text,
                    "constraints": safe_constraints,
                    "k": request.k,
                    "previous_answer": assistant_answer,
                },
                headers=headers,
                timeout=40.0,
            )
            tools_called.append("regenerate")
            if regenerate_response.status_code == 200:
                improved_draft_answer = regenerate_response.json().get("answer")
            else:
                status = "partial"
                regenerate_error = _build_upstream_error(regenerate_response, "regenerate")
                errors.append(regenerate_error)
                logger.error("AI engine regenerate failed", extra=regenerate_error)

    return search_data, critique_data, improved_draft_answer, status, tools_called, errors


# Get All Users
@router.get("/users", response_model=List[UserStats])
async def get_all_users(
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all users with their statistics"""
    logger.info(f"Admin viewing all users", extra={"admin_id": admin_user.id})
    
    docs_subq = (
        select(Document.owner_id.label("user_id"), func.count(Document.id).label("document_count"))
        .group_by(Document.owner_id)
        .subquery()
    )
    chats_subq = (
        select(ChatHistory.user_id.label("user_id"), func.count(ChatHistory.id).label("chat_count"))
        .group_by(ChatHistory.user_id)
        .subquery()
    )
    usage_subq = (
        select(APIUsage.user_id.label("user_id"), func.count(APIUsage.id).label("api_calls"))
        .group_by(APIUsage.user_id)
        .subquery()
    )

    result = await db.execute(
        select(
            User,
            func.coalesce(docs_subq.c.document_count, 0).label("document_count"),
            func.coalesce(chats_subq.c.chat_count, 0).label("chat_count"),
            func.coalesce(usage_subq.c.api_calls, 0).label("api_calls"),
        )
        .outerjoin(docs_subq, docs_subq.c.user_id == User.id)
        .outerjoin(chats_subq, chats_subq.c.user_id == User.id)
        .outerjoin(usage_subq, usage_subq.c.user_id == User.id)
        .order_by(User.id.asc())
        .offset(skip)
        .limit(limit)
    )
    rows = result.all()

    return [
        UserStats(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            document_count=document_count,
            chat_count=chat_count,
            total_api_calls=api_calls,
        )
        for user, document_count, chat_count, api_calls in rows
    ]


# Get API Usage Statistics
@router.get("/usage-stats", response_model=List[UsageStats])
async def get_usage_statistics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View API usage statistics by endpoint"""
    logger.info(f"Admin viewing usage stats", extra={"admin_id": admin_user.id})
    
    result = await db.execute(
        select(
            APIUsage.endpoint,
            func.count(APIUsage.id).label("total_calls"),
            func.sum(APIUsage.tokens).label("total_tokens"),
            func.avg(APIUsage.latency).label("avg_latency")
        )
        .group_by(APIUsage.endpoint)
    )
    stats = result.all()
    
    return [
        UsageStats(
            endpoint=stat.endpoint,
            total_calls=stat.total_calls,
            total_tokens=stat.total_tokens or 0,
            avg_latency=round(stat.avg_latency, 3) if stat.avg_latency else 0.0
        )
        for stat in stats
    ]


# Get System Statistics
@router.get("/system-stats", response_model=SystemStats)
async def get_system_statistics(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View overall system statistics"""
    logger.info(f"Admin viewing system stats", extra={"admin_id": admin_user.id})
    
    # Overall counts
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()
    
    total_documents_result = await db.execute(select(func.count(Document.id)))
    total_documents = total_documents_result.scalar()
    
    total_chats_result = await db.execute(select(func.count(ChatHistory.id)))
    total_chats = total_chats_result.scalar()
    
    total_api_calls_result = await db.execute(select(func.count(APIUsage.id)))
    total_api_calls = total_api_calls_result.scalar()
    

    return SystemStats(
        total_users=total_users,
        total_documents=total_documents,
        total_chats=total_chats,
        total_api_calls=total_api_calls
    )


# Get User's API Usage
@router.get("/users/{user_id}/usage")
async def get_user_usage(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View specific user's API usage"""
    logger.info(f"Admin viewing user usage", extra={"admin_id": admin_user.id, "target_user_id": user_id})
    
    result = await db.execute(
        select(APIUsage)
        .filter(APIUsage.user_id == user_id)
        .order_by(APIUsage.created_at.desc())
        .limit(100)
    )
    usage = result.scalars().all()

    total_calls_result = await db.execute(
        select(func.count(APIUsage.id)).filter(APIUsage.user_id == user_id)
    )
    total_calls = total_calls_result.scalar() or 0
    
    return {
        "user_id": user_id,
        "total_calls": total_calls,
        "returned_count": len(usage),
        "recent_usage": [
            {
                "endpoint": u.endpoint,
                "tokens": u.tokens,
                "latency": u.latency,
                "created_at": u.created_at
            }
            for u in usage
        ]
    }


# Get All Documents (Admin View)
@router.get("/documents")
async def get_all_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all documents across all users"""
    logger.info(f"Admin viewing all documents", extra={"admin_id": admin_user.id})
    
    total_result = await db.execute(select(func.count()).select_from(Document))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Document)
        .order_by(Document.id.desc())
        .limit(limit)
        .offset(offset)
    )
    docs = result.scalars().all()
    
    return {
        "limit": limit,
        "offset": offset,
        "total": total,
        "returned_count": len(docs),
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "owner_id": doc.owner_id,
                "index_status": doc.index_status,
                "chunk_count": doc.chunk_count
            }
            for doc in docs
        ]
    }


# Get All Chats (Admin View)
@router.get("/chats")
async def get_all_chats(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all chat history across all users"""
    logger.info(f"Admin viewing all chats", extra={"admin_id": admin_user.id})
    
    result = await db.execute(
        select(ChatHistory)
        .order_by(ChatHistory.created_at.desc())
        .limit(100)
    )
    chats = result.scalars().all()

    total_chats_result = await db.execute(select(func.count(ChatHistory.id)))
    total_chats = total_chats_result.scalar() or 0
    
    return {
        "total": total_chats,
        "returned_count": len(chats),
        "recent_chats": [
            {
                "id": chat.id,
                "user_id": chat.user_id,
                "message": chat.content[:100] + "..." if len(chat.content) > 100 else chat.content,
                "timestamp": chat.created_at
            }
            for chat in chats
        ]
    }


# Simplified Stats Endpoint
@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    admin = Depends(require_admin)
):
    """Admin-only: Quick overview of system statistics"""
    users_count = await db.execute(select(func.count(User.id)))
    docs_count = await db.execute(select(func.count(Document.id)))
    chats_count = await db.execute(select(func.count(ChatHistory.id)))
    utc_midnight = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    usage_today_count = await db.execute(
        select(func.count(APIUsage.id)).filter(
            APIUsage.created_at >= utc_midnight
        )
    )
    
    return {
        "users": users_count.scalar(),
        "documents": docs_count.scalar(),
        "chats": chats_count.scalar(),
        "usage_today": usage_today_count.scalar()
    }

@router.get("/debug/conversations/{conversation_id}")
async def debug_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """
    Admin-only: Debug a conversation with full RAG pipeline details.
    
    Returns:
    - All messages in the conversation
    - For the last user query: retrieved chunks, prompt length, document IDs,
      confidence score, and hallucination score
    """
    logger.info(f"Admin debugging conversation", extra={
        "admin_id": admin_user.id, 
        "conversation_id": conversation_id
    })
    
    # Get conversation
    conv_result = await db.execute(
        select(Conversation).filter(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get all messages
    result = await db.execute(
        select(ChatHistory)
        .filter(ChatHistory.conversation_id == conversation_id)
        .order_by(ChatHistory.created_at.asc())
    )
    chats = result.scalars().all()
    
    messages = [
        {
            "id": chat.id,
            "user_id": chat.user_id,
            "role": chat.role,
            "content": chat.content,
            "created_at": chat.created_at
        }
        for chat in chats
    ]
    
    # Find last user message to replay for debug info
    last_user_msg = None
    last_assistant_msg = None
    for chat in reversed(chats):
        if chat.role == "user" and last_user_msg is None:
            last_user_msg = chat
        if chat.role == "assistant" and last_assistant_msg is None:
            last_assistant_msg = chat
        if last_user_msg and last_assistant_msg:
            break
    
    debug_info = None
    if last_user_msg:
        # Call AI engine debug endpoint to get retrieval details
        try:
            def _safe_json(response: httpx.Response, context: str) -> dict:
                if response.status_code != 200:
                    return {}
                try:
                    return response.json()
                except ValueError as parse_error:
                    logger.error("Failed to parse AI engine JSON", extra={
                        "context": context,
                        "status_code": response.status_code,
                        "response_preview": response.text[:300],
                        "error": str(parse_error),
                    })
                    return {}

            async with httpx.AsyncClient() as client:
                # Get retrieved chunks
                search_response = await client.get(
                    f"{AI_ENGINE_URL}/debug/search-preview",
                    params={"query": last_user_msg.content, "k": 5},
                    headers={"X-Internal-API-Key": settings.INTERNAL_API_KEY},
                    timeout=30.0
                )
                search_data = _safe_json(search_response, "debug/search-preview")
                
                # Get confidence and hallucination scores
                if last_assistant_msg and search_data.get("chunks"):
                    critique_response = await client.post(
                        f"{AI_ENGINE_URL}/critique",
                        json={
                            "question": last_user_msg.content,
                            "answer": last_assistant_msg.content,
                            "sources": search_data.get("chunks", [])
                        },
                        headers={"X-Internal-API-Key": settings.INTERNAL_API_KEY},
                        timeout=30.0
                    )
                    critique_data = _safe_json(critique_response, "critique")
                else:
                    critique_data = {}
                
                # Build prompt to estimate length
                chunks_text = "\n\n".join([
                    c.get("text_preview", "") for c in search_data.get("chunks", [])
                ])
                estimated_prompt = f"System: You are an AI assistant.\n\nContext:\n{chunks_text}\n\nQuestion: {last_user_msg.content}"
                
                debug_info = {
                    "last_query": last_user_msg.content,
                    "retrieved_chunks": search_data.get("chunks", []),
                    "total_chunks_retrieved": search_data.get("results_count", 0),
                    "document_ids": list(set(
                        c.get("document_id") for c in search_data.get("chunks", []) 
                        if c.get("document_id")
                    )),
                    "prompt_length_chars": len(estimated_prompt),
                    "prompt_length_words": len(estimated_prompt.split()),
                    "confidence_score": critique_data.get("critique", {}).get("llm_critique", {}).get("overall_score"),
                    "hallucination_score": critique_data.get("critique", {}).get("hallucination_detection", {}).get("hallucination_score"),
                    "alignment_score": critique_data.get("critique", {}).get("hallucination_detection", {}).get("alignment_score"),
                    "critique_details": critique_data.get("critique", {})
                }
        except Exception as e:
            logger.error("Failed to get debug info from AI engine", extra={"error": str(e)}, exc_info=True)
            debug_info = {"error": "failed to fetch debug info", "error_code": "AI_DEBUG_FETCH_FAILED"}
    
    return {
        "conversation_id": conversation_id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "message_count": len(messages),
        "messages": messages,
        "debug_info": debug_info
    }


@router.post("/investigations/run", response_model=InvestigationRunResponse)
async def run_investigation(
    body: InvestigationRunRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only: run a read-only conversation investigation and persist audit metadata."""
    started_at = time.perf_counter()

    conv_result = await db.execute(
        select(Conversation).filter(Conversation.id == body.conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    chats_result = await db.execute(
        select(ChatHistory)
        .filter(ChatHistory.conversation_id == body.conversation_id)
        .order_by(ChatHistory.created_at.asc())
    )
    chats = chats_result.scalars().all()

    last_user_msg = None
    last_assistant_msg = None
    for chat in reversed(chats):
        if chat.role == "assistant" and last_assistant_msg is None:
            last_assistant_msg = chat
        if chat.role == "user" and last_user_msg is None:
            last_user_msg = chat
        if last_user_msg and last_assistant_msg:
            break

    if not last_user_msg:
        raise HTTPException(status_code=400, detail="No user message found in conversation")

    status = "completed"
    tools_called: List[str] = []
    search_data: Dict[str, Any] = {}
    critique_data: Dict[str, Any] = {}
    improved_draft_answer: Optional[str] = None
    error_details: List[Dict[str, Any]] = []

    try:
        search_data, critique_data, improved_draft_answer, status, tools_called, error_details = (
            await _call_ai_engine_for_investigation(
                query_text=last_user_msg.content,
                assistant_answer=last_assistant_msg.content if last_assistant_msg else None,
                request=body,
            )
        )
    except Exception as exc:
        status = "partial"
        logger.error("Investigation ai_engine calls failed", extra={
            "conversation_id": body.conversation_id,
            "admin_id": admin_user.id,
            "error": str(exc),
        }, exc_info=True)
        error_details.append({"context": "ai_engine", "status_code": None, "body": str(exc)})

    chunks = search_data.get("chunks", []) if isinstance(search_data, dict) else []
    evidence = InvestigationEvidence(
        retrieved_chunks=chunks,
        total_chunks_retrieved=search_data.get("results_count", 0) if isinstance(search_data, dict) else 0,
        document_ids=list({c.get("document_id") for c in chunks if c.get("document_id")}),
    )

    critique_root = critique_data.get("critique", {}) if isinstance(critique_data, dict) else {}
    llm_critique = critique_root.get("llm_critique", {}) if isinstance(critique_root, dict) else {}
    hallucination = critique_root.get("hallucination_detection", {}) if isinstance(critique_root, dict) else {}
    confidence_raw = llm_critique.get("overall_score")
    quality = InvestigationQualitySummary(
        confidence_score=(confidence_raw / 10.0) if isinstance(confidence_raw, (int, float)) else None,
        hallucination_score=hallucination.get("hallucination_score") if isinstance(hallucination, dict) else None,
        alignment_score=hallucination.get("alignment_score") if isinstance(hallucination, dict) else None,
    )

    diagnosis = _derive_diagnosis(body.instruction_intent, quality, evidence.total_chunks_retrieved)
    recommended_actions = _derive_recommended_actions(
        body.instruction_intent,
        quality,
        evidence.total_chunks_retrieved,
    )

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    audit = InvestigationAudit(
        investigator_user_id=admin_user.id,
        conversation_id=body.conversation_id,
        instruction_intent=body.instruction_intent,
        tools_called=json.dumps(tools_called),
        status=status,
        latency_ms=latency_ms,
        confidence_score=quality.confidence_score,
        hallucination_score=quality.hallucination_score,
        alignment_score=quality.alignment_score,
        diagnosis_summary=diagnosis[:1000],
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return InvestigationRunResponse(
        investigation_id=audit.id,
        conversation_id=body.conversation_id,
        instruction_intent=body.instruction_intent,
        diagnosis=diagnosis,
        supporting_evidence=evidence,
        quality_summary=quality,
        recommended_next_actions=recommended_actions,
        improved_draft_answer=improved_draft_answer,
        error_details=error_details,
        status=status,
        created_at=audit.created_at,
    )


@router.get("/investigations/{investigation_id}")
async def get_investigation(
    investigation_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only: fetch one investigation audit record."""
    result = await db.execute(
        select(InvestigationAudit).filter(InvestigationAudit.id == investigation_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Investigation not found")

    return {
        "id": row.id,
        "investigator_user_id": row.investigator_user_id,
        "conversation_id": row.conversation_id,
        "instruction_intent": row.instruction_intent,
        "tools_called": json.loads(row.tools_called or "[]"),
        "status": row.status,
        "latency_ms": row.latency_ms,
        "confidence_score": row.confidence_score,
        "hallucination_score": row.hallucination_score,
        "alignment_score": row.alignment_score,
        "diagnosis_summary": row.diagnosis_summary,
        "created_at": row.created_at,
    }


@router.get("/investigations/conversation/{conversation_id}")
async def list_investigations_for_conversation(
    conversation_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only: list recent investigations for a conversation."""
    result = await db.execute(
        select(InvestigationAudit)
        .filter(InvestigationAudit.conversation_id == conversation_id)
        .order_by(InvestigationAudit.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()

    return {
        "conversation_id": conversation_id,
        "returned_count": len(rows),
        "items": [
            {
                "id": row.id,
                "instruction_intent": row.instruction_intent,
                "status": row.status,
                "latency_ms": row.latency_ms,
                "confidence_score": row.confidence_score,
                "hallucination_score": row.hallucination_score,
                "alignment_score": row.alignment_score,
                "diagnosis_summary": row.diagnosis_summary,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }

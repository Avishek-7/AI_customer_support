from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List
from datetime import datetime, timedelta, date
from core.database import get_db
from core.roles import require_admin
from models.user import User
from models.document import Document
from models.chat import ChatHistory
from models.usage import APIUsage
from pydantic import BaseModel
from typing import Optional
from utils.logger import get_logger

logger = get_logger("backend.api.admin")

router = APIRouter(prefix="/admin", tags=["admin"])


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
    users_last_24h: int
    documents_last_24h: int


# Get All Users
@router.get("/users", response_model=List[UserStats])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all users with their statistics"""
    logger.info(f"Admin viewing all users", extra={"admin_id": admin_user.id})
    
    result = await db.execute(select(User))
    users = result.scalars().all()
    user_stats = []
    
    for user in users:
        doc_count_result = await db.execute(
            select(func.count(Document.id)).filter(Document.owner_id == user.id)
        )
        doc_count = doc_count_result.scalar()
        
        chat_count_result = await db.execute(
            select(func.count(ChatHistory.id)).filter(ChatHistory.user_id == user.id)
        )
        chat_count = chat_count_result.scalar()
        
        api_calls_result = await db.execute(
            select(func.count(APIUsage.id)).filter(APIUsage.user_id == user.id)
        )
        api_calls = api_calls_result.scalar()
        
        user_stats.append(UserStats(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            document_count=doc_count,
            chat_count=chat_count,
            total_api_calls=api_calls
        ))
    
    return user_stats


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
    
    # Last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    users_last_24h = 0  # Requires created_at column
    documents_last_24h = 0  # Requires created_at column
    
    return SystemStats(
        total_users=total_users,
        total_documents=total_documents,
        total_chats=total_chats,
        total_api_calls=total_api_calls,
        users_last_24h=0,  # Requires created_at column
        documents_last_24h=0  # Requires created_at column
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
    
    return {
        "user_id": user_id,
        "total_calls": len(usage),
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
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all documents across all users"""
    logger.info(f"Admin viewing all documents", extra={"admin_id": admin_user.id})
    
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    
    return {
        "total": len(docs),
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
        .order_by(ChatHistory.timestamp.desc())
        .limit(100)
    )
    chats = result.scalars().all()
    
    return {
        "total": len(chats),
        "recent_chats": [
            {
                "id": chat.id,
                "user_id": chat.user_id,
                "message": chat.message[:100] + "..." if len(chat.message) > 100 else chat.message,
                "timestamp": chat.timestamp
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
    usage_today_count = await db.execute(
        select(func.count(APIUsage.id)).filter(
            APIUsage.created_at >= date.today()
        )
    )
    
    return {
        "users": users_count.scalar(),
        "documents": docs_count.scalar(),
        "chats": chats_count.scalar(),
        "usage_today": usage_today_count.scalar()
    }

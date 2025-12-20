from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta, date
from core.database import get_db
from core.roles import require_admin
from models.user import User
from models.document import Document
from models.chat import ChatHistory
from models.usage import APIUsage
from pydantic import BaseModel
from utils.logger import get_logger

logger = get_logger("backend.api.admin")

router = APIRouter(prefix="/admin", tags=["admin"])


# Response Models
class UserStats(BaseModel):
    id: int
    name: str
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
def get_all_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all users with their statistics"""
    logger.info(f"Admin viewing all users", extra={"admin_id": admin_user.id})
    
    users = db.query(User).all()
    user_stats = []
    
    for user in users:
        doc_count = db.query(Document).filter(Document.owner_id == user.id).count()
        chat_count = db.query(ChatHistory).filter(ChatHistory.user_id == user.id).count()
        api_calls = db.query(APIUsage).filter(APIUsage.user_id == user.id).count()
        
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
def get_usage_statistics(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View API usage statistics by endpoint"""
    logger.info(f"Admin viewing usage stats", extra={"admin_id": admin_user.id})
    
    stats = (
        db.query(
            APIUsage.endpoint,
            func.count(APIUsage.id).label("total_calls"),
            func.sum(APIUsage.tokens).label("total_tokens"),
            func.avg(APIUsage.latency).label("avg_latency")
        )
        .group_by(APIUsage.endpoint)
        .all()
    )
    
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
def get_system_statistics(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View overall system statistics"""
    logger.info(f"Admin viewing system stats", extra={"admin_id": admin_user.id})
    
    # Overall counts
    total_users = db.query(User).count()
    total_documents = db.query(Document).count()
    total_chats = db.query(ChatHistory).count()
    total_api_calls = db.query(APIUsage).count()
    
    # Last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    users_last_24h = db.query(User).filter(User.id >= 0).count()  # Placeholder - needs created_at field
    documents_last_24h = db.query(Document).count()  # Placeholder - needs created_at field
    
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
def get_user_usage(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View specific user's API usage"""
    logger.info(f"Admin viewing user usage", extra={"admin_id": admin_user.id, "target_user_id": user_id})
    
    usage = db.query(APIUsage).filter(APIUsage.user_id == user_id).order_by(APIUsage.created_at.desc()).limit(100).all()
    
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
def get_all_documents(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all documents across all users"""
    logger.info(f"Admin viewing all documents", extra={"admin_id": admin_user.id})
    
    docs = db.query(Document).all()
    
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
def get_all_chats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: View all chat history across all users"""
    logger.info(f"Admin viewing all chats", extra={"admin_id": admin_user.id})
    
    chats = db.query(ChatHistory).order_by(ChatHistory.timestamp.desc()).limit(100).all()
    
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
def admin_stats(
    db: Session = Depends(get_db),
    admin = Depends(require_admin)
):
    """Admin-only: Quick overview of system statistics"""
    return {
        "users": db.query(User).count(),
        "documents": db.query(Document).count(),
        "chats": db.query(ChatHistory).count(),
        "usage_today": db.query(APIUsage).filter(
            APIUsage.created_at >= date.today()
        ).count()
    }

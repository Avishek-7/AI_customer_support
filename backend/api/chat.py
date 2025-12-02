from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import httpx
from core.database import get_db
from core.security import get_current_user
from core.config import settings
from models.user import User
from models.document import Document

router = APIRouter(prefix="/chat", tags=["chat"])

AI_ENGINE_URL = settings.AI_ENGINE_URL

# Request and Response Models
class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = "You are an AI customer support assistant."

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
    
    # Fetch user's documents from DB
    user_docs = (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .all()
    )

    if not user_docs:
        raise HTTPException(
            status_code=400,
            detail="You have no indexed documents. Please upload a PDF first."
        )
    
    document_ids = [doc.id for doc in user_docs]

    # Call AI Engine
    async with httpx.AsyncClient() as client:
        try:
            ai_response = await client.post(
                f"{AI_ENGINE_URL}/query",
                json={
                    "query": body.message,
                    "system_prompt": body.system_prompt,
                    "document_ids": document_ids,
                    "k": 5,
                },
                timeout=40.0,
            )
            ai_response.raise_for_status()
        except Exception as e:
            print(f"[AI ENGINE ERROR] {e}")
            raise HTTPException(
                status_code=500,
                detail="AI engine is unavailable. Please try again later."
            )
    
    data = ai_response.json()

    # Return formatted answer to frontend
    return ChatResponse(
        answer=data["answer"],
        sources=data["sources"]
    )
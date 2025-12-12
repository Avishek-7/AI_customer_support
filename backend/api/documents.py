from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import httpx
from core.database import get_db
from core.config import settings
from models.user import User
from core.security import get_current_user
from models.document import Document
from schemas.document_schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUpdate,
    DocumentDeleteResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentStatusUpdateRequest,
)
from utils.pdf_loader import extract_text_from_pdf

router = APIRouter(prefix="/documents", tags=["documents"])

AI_ENGINE_URL = settings.AI_ENGINE_URL

# ------ Upload Document -----
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Extract text from PDF
    pdf_bytes = await file.read()
    content = extract_text_from_pdf(pdf_bytes)

    # Store document in DB
    document_db = Document(
        title=title,
        content=content,
        owner_id=current_user.id
    )
    
    db.add(document_db)
    db.commit()
    db.refresh(document_db)

    # Call AI Engine to index this document
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{AI_ENGINE_URL}/index-document",
                json={
                    "document_id": document_db.id,
                    "title": document_db.title,
                    "content": document_db.content,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
        except Exception as e:
            # You might choose to log this but not fail the whole request
            print(f"[AI ENGINE ERROR - index-document] {e}")

    return document_db

# ------ Get User Documents -----
@router.get("/", response_model=DocumentListResponse)
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    docs = db.query(Document).filter(Document.owner_id == current_user.id).all()
    return DocumentListResponse(documents=docs)

# ------ Get single Document -----
@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.owner_id == current_user.id)
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc

# ------ Update Document -----
@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: int,
    update_data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.owner_id == current_user.id)
        .first()
    )

    if not doc: 
        raise HTTPException(status_code=404, detail="Document not found")
    
    if update_data.title:
        doc.title = update_data.title

    if update_data.content:
        doc.content = update_data.content

    db.commit()
    db.refresh(doc)

    # Tell AI Engine to re-index this updated document
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{AI_ENGINE_URL}/update-document",
                json={
                    "document_id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[AI ENGINE ERROR - update-document] {e}")
    
    return doc

# ------ Delete Document -----
@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.owner_id == current_user.id)
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from AI Engine FAISS index
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.delete(
                f"{AI_ENGINE_URL}/delete-document/{doc.id}"
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[AI ENGINE ERROR - delete-document] {e}")
    
    # Delete from database
    db.delete(doc)
    db.commit()

    return DocumentDeleteResponse(detail="Document deleted successfully")

# ------ Search Documents -----
@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    search_req: DocumentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = f"%{search_req.query.lower()}%"

    docs = (
        db.query(Document)
        .filter(
            Document.owner_id == current_user.id,
            Document.content.ilike(query)
        )
        .all()
    )

    return DocumentSearchResponse(documents=docs)


# ------ Update Document Status from AI Engine -----
@router.post("/update-status")
def update_document_status(
    body: DocumentStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == body.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.index_status = body.status
    
    if body.chunk_count is not None:
        doc.chunk_count = body.chunk_count

    db.commit()
    return {"detail": "Status updated"}


@router.get("/status/{doc_id}")
def get_document_status(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "document_id": doc.id,
        "status": doc.index_status or "pending",
        "chunk_count": doc.chunk_count or 0
    }
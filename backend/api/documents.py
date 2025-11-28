from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
# from core.security import hash_password, verify_password, create_access_token
from models.user import User
from core.security import get_current_user
from models.document import Document
from schemas.document_schemas import (
    DocumentBase,
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
    DocumentUpdate,
    DocumentDeleteResponse,
    DocumentShareRequest,
    DocumentShareResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUpload,
)
from utils.pdf_loader import extract_text_from_pdf

router = APIRouter(prefix="/documents", tags=["documents"])

# ------ Upload Document -----
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    title: str,
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
def update_document(
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
    
    return doc

# ------ Delete Document -----
@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
def delete_document(
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


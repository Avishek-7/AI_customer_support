from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import httpx
import time
from core.database import get_db
from core.config import settings
from models.user import User
from core.security import get_current_user
from core.rate_limit import rate_limit
from models.document import Document
from rq import Queue
from redis import Redis
from jobs.tasks import index_document_task
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
from utils.logger import get_logger
from utils.usage_tracker import track_usage
from utils.permissions import check_document_ownership

logger = get_logger("backend.api.documents")

router = APIRouter(prefix="/documents", tags=["documents"])

AI_ENGINE_URL = settings.AI_ENGINE_URL

# Initialize RQ queue
queue = Queue(connection=Redis())

# ------ Upload Document -----
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Rate limit uploads (20 uploads per hour per user)
    rate_limit(current_user.id, limit=20, window=3600)
    
    # Start timer for latency tracking
    start_time = time.time()
    
    logger.info(f"Document upload started", extra={
        "user_id": current_user.id,
        "title": title,
        "file_name": file.filename
    })
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        logger.warning(f"Invalid file type", extra={"file_name": file.filename})
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Extract text from PDF
    pdf_bytes = await file.read()
    content = extract_text_from_pdf(pdf_bytes)
    logger.info(f"PDF text extracted", extra={"content_length": len(content)})

    # Store document in DB
    document_db = Document(
        title=title,
        content=content,
        owner_id=current_user.id
    )
    
    db.add(document_db)
    db.commit()
    db.refresh(document_db)
    logger.info(f"Document saved to database", extra={"document_id": document_db.id})

    # Enqueue indexing job to background queue
    job = queue.enqueue(index_document_task, document_db.id, document_db.title, document_db.content)
    logger.info(f"Document indexing job enqueued", extra={
        "document_id": document_db.id,
        "job_id": job.id
    })

    # Track API usage
    latency = time.time() - start_time
    tokens = len(content.split())  # Approximate token count based on content
    track_usage(db, current_user.id, "/documents/upload", tokens, latency)

    return document_db

# ------ Get User Documents -----
@router.get("/", response_model=DocumentListResponse)
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Fetching user documents", extra={"user_id": current_user.id})
    docs = db.query(Document).filter(Document.owner_id == current_user.id).all()
    logger.info(f"Documents retrieved", extra={
        "user_id": current_user.id, 
        "count": len(docs),
        "document_ids": [doc.id for doc in docs],
        "document_titles": [doc.title for doc in docs]
    })
    return DocumentListResponse(documents=docs)

# ------ Get single Document -----
@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Fetching document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    # Check ownership - raises 404 if not found or access denied
    doc = check_document_ownership(db, doc_id, current_user)
    
    logger.info(f"Document retrieved", extra={"doc_id": doc_id})
    return doc

# ------ Update Document -----
@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: int,
    update_data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Updating document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    # Check ownership - raises 404 if not found or access denied
    doc = check_document_ownership(db, doc_id, current_user)
    
    if update_data.title:
        doc.title = update_data.title

    if update_data.content:
        doc.content = update_data.content

    db.commit()
    db.refresh(doc)
    logger.info(f"Document updated in database", extra={"doc_id": doc_id})

    # Enqueue re-indexing job to background queue
    job = queue.enqueue(index_document_task, doc.id, doc.title, doc.content)
    logger.info(f"Document re-indexing job enqueued", extra={
        "doc_id": doc_id,
        "job_id": job.id
    })
    
    return doc

# ------ Delete Document -----
@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Deleting document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    # Check ownership - raises 404 if not found or access denied
    doc = check_document_ownership(db, doc_id, current_user)
    
    # Delete from AI Engine FAISS index
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.delete(
                f"{AI_ENGINE_URL}/delete-document/{doc.id}"
            )
            resp.raise_for_status()
            logger.info(f"Document deleted from AI engine", extra={"doc_id": doc_id})
        except Exception as e:
            logger.error(f"AI engine delete error", extra={"doc_id": doc_id, "error": str(e)})
    
    # Delete from database
    db.delete(doc)
    db.commit()
    logger.info(f"Document deleted from database", extra={"doc_id": doc_id})

    return DocumentDeleteResponse(detail="Document deleted successfully")

# ------ Search Documents -----
@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    search_req: DocumentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Searching documents", extra={"user_id": current_user.id, "query": search_req.query})
    query = f"%{search_req.query.lower()}%"

    docs = (
        db.query(Document)
        .filter(
            Document.owner_id == current_user.id,
            Document.content.ilike(query)
        )
        .all()
    )

    logger.info(f"Search completed", extra={"user_id": current_user.id, "results_count": len(docs)})
    return DocumentSearchResponse(documents=docs)


# ------ Update Document Status from AI Engine -----
@router.post("/update-status")
def update_document_status(
    body: DocumentStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"Updating document status", extra={
        "document_id": body.document_id,
        "status": body.status,
        "chunk_count": body.chunk_count
    })
    
    doc = db.query(Document).filter(Document.id == body.document_id).first()
    if not doc:
        logger.warning(f"Document not found for status update", extra={"document_id": body.document_id})
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.index_status = body.status
    
    if body.chunk_count is not None:
        doc.chunk_count = body.chunk_count

    db.commit()
    logger.info(f"Document status updated", extra={"document_id": body.document_id, "status": body.status})
    return {"detail": "Status updated"}


@router.get("/status/{doc_id}")
def get_document_status(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.debug(f"Getting document status", extra={"doc_id": doc_id})
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        logger.warning(f"Document not found for status check", extra={"doc_id": doc_id})
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "document_id": doc.id,
        "status": doc.index_status or "pending",
        "chunk_count": doc.chunk_count or 0
    }


# ------ Re-index Document (force re-chunk and re-embed) -----
@router.post("/{doc_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Force re-index a document in the AI engine.
    Useful when chunking/embedding needs to be regenerated.
    """
    logger.info(f"Re-indexing document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.owner_id == current_user.id)
        .first()
    )
    
    if not doc:
        logger.warning(f"Document not found for re-index", extra={"doc_id": doc_id})
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update status to processing
    doc.index_status = "processing"
    db.commit()
    
    # Call AI Engine to re-index (update = delete old + re-index)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.put(
                f"{AI_ENGINE_URL}/update-document",
                json={
                    "document_id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            result = resp.json()
            doc.chunk_count = result.get("chunks_indexed", 0)
            doc.index_status = "completed"
            db.commit()
            logger.info(f"Document re-indexed successfully", extra={
                "doc_id": doc_id,
                "chunks": doc.chunk_count
            })
        except Exception as e:
            doc.index_status = "failed"
            db.commit()
            logger.error(f"AI engine re-index error", extra={"doc_id": doc_id, "error": str(e)})
            raise HTTPException(status_code=500, detail=f"Re-indexing failed: {str(e)}")
    
    db.refresh(doc)
    return doc
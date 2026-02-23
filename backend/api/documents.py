from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import time
from core.database import get_db
from core.config import settings
from core.error_handler import ErrorHandler
from models.user import User
from core.security import get_current_user
from core.rate_limit import rate_limit
from models.document import Document
from jobs.background import index_document_task
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


# ------ Upload Document -----
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
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
        logger.warning(f"Invalid file type", extra={
            "user_id": current_user.id,
            "file_name": file.filename
        })
        raise ErrorHandler.bad_request("Only PDF files are allowed")
    
    # Extract text from PDF (run in thread to avoid blocking)
    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        pdf_bytes = await file.read()
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            content = await loop.run_in_executor(executor, extract_text_from_pdf, pdf_bytes)
        logger.info(f"PDF text extracted", extra={
            "user_id": current_user.id,
            "content_length": len(content)
        })
    except Exception as e:
        logger.error(f"PDF extraction failed", extra={
            "user_id": current_user.id,
            "file_name": file.filename,
            "error": str(e)
        })
        raise ErrorHandler.bad_request("Failed to extract PDF content. Ensure the file is a valid PDF.")

    # Store document in DB
    document_db = Document(
        title=title,
        content=content,
        owner_id=current_user.id
    )
    
    db.add(document_db)
    await db.commit()
    await db.refresh(document_db)
    logger.info(f"Document saved to database", extra={"document_id": document_db.id})

    # Enqueue indexing job to background task
    background_tasks.add_task(index_document_task, document_db.id)
    logger.info(
        "Document indexing task enqueued",
        extra={"document_id": document_db.id}
    )

    # Track API usage
    latency = time.time() - start_time
    tokens = len(content.split())  # Approximate token count based on content
    await track_usage(db, current_user.id, "/documents/upload", tokens, latency)

    return document_db

# ------ Get User Documents -----
@router.get("/", response_model=DocumentListResponse)
async def get_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start_time = time.time()
    
    logger.info(f"Fetching user documents", extra={"user_id": current_user.id})
    result = await db.execute(
        select(Document).filter(Document.owner_id == current_user.id)
    )
    docs = result.scalars().all()
    
    latency = time.time() - start_time
    logger.info(f"Documents retrieved", extra={
        "user_id": current_user.id, 
        "count": len(docs),
        "document_ids": [doc.id for doc in docs],
        "latency": f"{latency:.3f}s"
    })
    return DocumentListResponse(documents=docs)

# ------ Get single Document -----
@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Fetching document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    # Check ownership - raises 404 if not found or access denied
    doc = await check_document_ownership(db, doc_id, current_user)
    
    logger.info(f"Document retrieved", extra={"doc_id": doc_id})
    return doc

# ------ Update Document -----
@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: int,
    update_data: DocumentUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Updating document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    # Check ownership - raises 404 if not found or access denied
    doc = await check_document_ownership(db, doc_id, current_user)
    
    if update_data.title is not None:
        doc.title = update_data.title

    if update_data.content is not None:
        doc.content = update_data.content

    await db.commit()
    await db.refresh(doc)
    logger.info(f"Document updated in database", extra={"doc_id": doc_id})

    # Enqueue re-indexing job to background task
    background_tasks.add_task(index_document_task, doc.id)
    logger.info(
        "Document re-indexing task enqueued",
        extra={"doc_id": doc.id}
    )
    
    return doc
# ------ Delete Document -----
@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start_time = time.time()
    
    logger.info(f"Deleting document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    # Check ownership - raises 404 if not found or access denied
    doc = await check_document_ownership(db, doc_id, current_user)
    
    # Delete from AI Engine FAISS index
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.delete(
                f"{AI_ENGINE_URL}/delete-document/{doc.id}",
                timeout=30.0
            )
            resp.raise_for_status()
            logger.info(f"Document deleted from AI engine", extra={"doc_id": doc_id})
        except httpx.HTTPError as e:
            # Log but don't fail - DB delete is the important one
            logger.warning(f"AI engine delete failed (continuing)", extra={"doc_id": doc_id, "error": str(e)})
        except Exception as e:
            logger.error(f"AI engine delete error", extra={"doc_id": doc_id, "error": str(e)})
    
    # Delete from database
    try:
        await db.delete(doc)
        await db.commit()
        
        latency = time.time() - start_time
        logger.info(f"Document deleted from database", extra={
            "user_id": current_user.id,
            "doc_id": doc_id,
            "latency": f"{latency:.3f}s"
        })
    except Exception as e:
        await db.rollback()
        logger.error(f"Database delete failed", extra={
            "user_id": current_user.id,
            "doc_id": doc_id,
            "error": str(e)
        })
        raise ErrorHandler.internal_error("Failed to delete document from database")

    return DocumentDeleteResponse(detail="Document deleted successfully")

# ------ Search Documents -----
@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    search_req: DocumentSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start_time = time.time()
    
    logger.info(f"Searching documents", extra={
        "user_id": current_user.id,
        "query": search_req.query
    })
    query = f"%{search_req.query.lower()}%"

    result = await db.execute(
        select(Document).filter(
            Document.owner_id == current_user.id,
            Document.content.ilike(query)
        )
    )
    docs = result.scalars().all()

    latency = time.time() - start_time
    logger.info(f"Search completed", extra={
        "user_id": current_user.id,
        "query": search_req.query,
        "results_count": len(docs),
        "latency": f"{latency:.3f}s"
    })
    return DocumentSearchResponse(documents=docs)


# ------ Update Document Status from AI Engine -----
@router.post("/update-status")
async def update_document_status(
    body: DocumentStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    internal_api_key: str | None = Header(default=None, alias="X-Internal-API-Key"),
):
    if not internal_api_key or internal_api_key != settings.INTERNAL_API_KEY:
        raise ErrorHandler.forbidden("Invalid internal API key")

    logger.info(f"Updating document status", extra={
        "document_id": body.document_id,
        "status": body.status,
        "chunk_count": body.chunk_count
    })
    
    result = await db.execute(select(Document).filter(Document.id == body.document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        logger.warning(f"Document not found for status update", extra={"document_id": body.document_id})
        raise ErrorHandler.not_found("Document not found")
    
    try:
        doc.index_status = body.status
        
        if body.chunk_count is not None:
            doc.chunk_count = body.chunk_count

        await db.commit()
        logger.info(f"Document status updated", extra={
            "document_id": body.document_id,
            "status": body.status
        })
        return {"detail": "Status updated"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update document status", extra={
            "document_id": body.document_id,
            "error": str(e)
        })
        raise ErrorHandler.internal_error("Failed to update document status")


@router.get("/status/{doc_id}")
async def get_document_status(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.debug(f"Getting document status", extra={
        "user_id": current_user.id,
        "doc_id": doc_id
    })
    result = await db.execute(
        select(Document).filter(
            Document.id == doc_id,
            Document.owner_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        logger.warning(f"Document not found for status check", extra={
            "user_id": current_user.id,
            "doc_id": doc_id
        })
        raise ErrorHandler.not_found("Document not found")
    
    return {
        "document_id": doc.id,
        "status": doc.index_status or "pending",
        "chunk_count": doc.chunk_count or 0
    }


# ------ Re-index Document (force re-chunk and re-embed) -----
@router.post("/{doc_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Force re-index a document in the AI engine.
    Useful when chunking/embedding needs to be regenerated.
    """
    # Rate limit reindex operations (10 per hour)
    rate_limit(current_user.id, limit=10, window=3600)
    
    start_time = time.time()
    logger.info(f"Re-indexing document", extra={"user_id": current_user.id, "doc_id": doc_id})
    
    result = await db.execute(
        select(Document).filter(
            Document.id == doc_id,
            Document.owner_id == current_user.id
        )
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        logger.warning(f"Document not found for re-index", extra={
            "user_id": current_user.id,
            "doc_id": doc_id
        })
        raise ErrorHandler.not_found("Document not found")
    
    # Update status to processing
    try:
        doc.index_status = "processing"
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to mark document for re-indexing", extra={
            "doc_id": doc_id,
            "error": str(e)
        })
        raise ErrorHandler.internal_error("Failed to start re-indexing")
    
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
            await db.commit()
            
            latency = time.time() - start_time
            logger.info(f"Document re-indexed successfully", extra={
                "user_id": current_user.id,
                "doc_id": doc_id,
                "chunks": doc.chunk_count,
                "latency": f"{latency:.3f}s"
            })
            
            # Track usage
            tokens = len(doc.content.split())
            try:
                await track_usage(db, current_user.id, "/documents/{doc_id}/reindex", tokens, latency)
            except Exception as e:
                logger.error(f"Failed to track reindex usage", extra={
                    "user_id": current_user.id,
                    "error": str(e)
                })
        except httpx.TimeoutException:
            doc.index_status = "failed"
            await db.commit()
            logger.error(f"AI engine re-index timeout", extra={"doc_id": doc_id})
            raise ErrorHandler.service_unavailable("Re-indexing is taking too long. Please try again later.")
        except httpx.HTTPError as e:
            doc.index_status = "failed"
            await db.commit()
            logger.error(f"AI engine re-index error", extra={"doc_id": doc_id, "error": str(e)})
            raise ErrorHandler.service_unavailable("AI engine is unavailable. Please try again later.")
        except Exception as e:
            doc.index_status = "failed"
            try:
                await db.commit()
            except Exception:
                await db.rollback()
            logger.error(f"Unexpected re-index error", extra={"doc_id": doc_id, "error": str(e)})
            raise ErrorHandler.internal_error("An unexpected error occurred during re-indexing")
    
    await db.refresh(doc)
    return doc
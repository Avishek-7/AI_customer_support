import ipaddress
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from pydantic import BaseModel
from typing import List, Dict, Any
from core.database import get_db
from core.config import settings
from models.vector_meta import VectorMetadata
from models.document import Document
from utils.logger import get_logger

logger = get_logger("backend.api.vectors")

router = APIRouter(prefix="/vectors", tags=["vectors"])


class VectorMetadataSync(BaseModel):
    """Schema for syncing vector metadata from AI engine"""
    metadata: List[Dict[str, Any]]


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_internal_ip(value: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(normalized)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def require_service_auth(
    request: Request,
    internal_api_key: str | None = Header(default=None, alias="X-Internal-API-Key"),
) -> None:
    client_ip = _get_client_ip(request)
    if not internal_api_key:
        logger.warning("Missing internal API key for vector endpoint", extra={"client_ip": client_ip})
        raise HTTPException(status_code=401, detail="Missing internal API key")

    if not secrets.compare_digest(internal_api_key or "", settings.INTERNAL_API_KEY or ""):
        logger.warning("Invalid internal API key for vector endpoint", extra={"client_ip": client_ip})
        raise HTTPException(status_code=401, detail="Invalid internal API key")


def require_internal_network(request: Request) -> None:
    client_ip = _get_client_ip(request)
    if not _is_internal_ip(client_ip):
        logger.warning("Blocked non-internal access to sensitive vector endpoint", extra={"client_ip": client_ip})
        raise HTTPException(status_code=403, detail="Sensitive endpoint is restricted to internal network")


@router.post("/sync")
async def sync_vector_metadata(
    body: VectorMetadataSync,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_service_auth),
    _network: None = Depends(require_internal_network),
):
    """
    Sync vector metadata from FAISS to PostgreSQL database.
    This enables hybrid storage: fast similarity search in FAISS + SQL queries in PostgreSQL.
    
    Called by AI engine after indexing documents.
    """
    logger.info(f"Syncing vector metadata", extra={"count": len(body.metadata)})
    
    try:
        # Delete all existing metadata (we're doing full sync from FAISS)
        await db.execute(sql_delete(VectorMetadata))

        requested_document_ids = {
            meta.get("document_id")
            for meta in body.metadata
            if meta.get("document_id") is not None
        }
        valid_document_ids = set()
        if requested_document_ids:
            docs_result = await db.execute(
                select(Document.id).filter(Document.id.in_(requested_document_ids))
            )
            valid_document_ids = set(docs_result.scalars().all())
        
        # Insert new metadata
        synced_count = 0
        faiss_pos = 0
        for meta in body.metadata:
            document_id = meta.get("document_id")
            
            # Verify document exists
            if document_id not in valid_document_ids:
                logger.warning(f"Document {document_id} not found, skipping vector metadata")
                continue
            
            vector_meta = VectorMetadata(
                document_id=document_id,
                chunk_index=meta.get("chunk_id", 0),
                text=meta.get("text", ""),
                faiss_index=faiss_pos,
                chunk_length=len(meta.get("text", ""))
            )
            db.add(vector_meta)
            synced_count += 1
            faiss_pos += 1
        
        await db.commit()
        
        logger.info(f"Vector metadata synced successfully", extra={
            "total_received": len(body.metadata),
            "synced": synced_count
        })
        
        return {
            "status": "success",
            "synced": synced_count,
            "total": len(body.metadata)
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to sync vector metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync metadata: {str(e)}")


@router.delete("/document/{document_id}")
async def delete_vector_metadata(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_service_auth),
    _network: None = Depends(require_internal_network),
):
    """
    Delete all vector metadata for a specific document.
    Called by AI engine when a document is deleted from FAISS.
    """
    logger.info(f"Deleting vector metadata", extra={"document_id": document_id})
    
    try:
        result = await db.execute(
            sql_delete(VectorMetadata).filter(
                VectorMetadata.document_id == document_id
            )
        )
        deleted_count = result.rowcount
        
        await db.commit()
        
        logger.info(f"Vector metadata deleted", extra={
            "document_id": document_id,
            "deleted_count": deleted_count
        })
        
        return {
            "status": "success",
            "document_id": document_id,
            "deleted": deleted_count
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete vector metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete metadata: {str(e)}")


@router.get("/document/{document_id}")
async def get_vector_metadata(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_service_auth),
):
    """
    Get all vector metadata for a specific document.
    Useful for debugging and analytics.
    """
    logger.info(f"Fetching vector metadata", extra={"document_id": document_id})
    
    result = await db.execute(
        select(VectorMetadata).filter(
            VectorMetadata.document_id == document_id
        ).order_by(VectorMetadata.chunk_index)
    )
    metadata = result.scalars().all()
    
    return {
        "document_id": document_id,
        "chunk_count": len(metadata),
        "chunks": [
            {
                "id": m.id,
                "chunk_index": m.chunk_index,
                "text_preview": ((m.text or "")[:100] + "...") if len(m.text or "") > 100 else (m.text or ""),
                "text_length": len(m.text or ""),
                "faiss_index": m.faiss_index,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in metadata
        ]
    }


@router.get("/stats")
async def get_vector_stats(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_service_auth),
):
    """
    Get statistics about vector storage.
    Shows how many vectors are stored per document.
    """
    logger.info("Fetching vector statistics")
    
    from sqlalchemy import func
    
    # Count vectors per document
    result = await db.execute(
        select(
            VectorMetadata.document_id,
            func.count(VectorMetadata.id).label("vector_count"),
            func.sum(VectorMetadata.chunk_length).label("total_chars")
        ).group_by(VectorMetadata.document_id)
    )
    stats = result.all()
    
    total_vectors_result = await db.execute(select(func.count(VectorMetadata.id)))
    total_vectors = total_vectors_result.scalar()
    
    total_documents_result = await db.execute(
        select(func.count(func.distinct(VectorMetadata.document_id)))
    )
    total_documents = total_documents_result.scalar()
    
    return {
        "total_vectors": total_vectors,
        "total_documents": total_documents,
        "per_document": [
            {
                "document_id": stat.document_id,
                "vector_count": stat.vector_count,
                "total_chars": stat.total_chars
            }
            for stat in stats
        ]
    }

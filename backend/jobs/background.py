"""
Background tasks for document processing.

Uses FastAPI's BackgroundTasks for simple async background processing.
No external dependencies like Celery or RabbitMQ required.
"""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from core.database import AsyncSessionLocal
from core.config import settings
from models.document import Document
from utils.logger import get_logger

logger = get_logger("backend.jobs.background")


async def index_document_task(document_id: int) -> None:
    """Background task to index a document via AI engine API.
    
    Creates its own database session since this runs outside the request context.
    """
    logger.info(f"Starting document indexing", extra={"document_id": document_id})
    
    async with AsyncSessionLocal() as db:
        try:
            # Fetch the document
            result = await db.execute(
                select(Document).filter(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                logger.error(f"Document not found", extra={"document_id": document_id})
                return
            
            # Update status to indexing
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(index_status="indexing")
            )
            await db.commit()
            
            # Call AI engine to index
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{settings.AI_ENGINE_URL}/index-document",
                    json={
                        "document_id": document.id,
                        "title": document.title,
                        "content": document.content,
                    },
                )
                response.raise_for_status()
                result_data = response.json()
            
            # Update status to indexed
            chunk_count = result_data.get("chunks_indexed", 0)
            await db.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(index_status="indexed", chunk_count=chunk_count)
            )
            await db.commit()
            
            logger.info(
                f"Document indexed successfully",
                extra={"document_id": document_id, "chunks": chunk_count}
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"AI engine indexing failed",
                extra={"document_id": document_id, "status": e.response.status_code},
                exc_info=True,
            )
            try:
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(index_status="failed")
                )
                await db.commit()
            except Exception as db_error:
                await db.rollback()
                logger.error("Failed to update document status after HTTPStatusError", extra={
                    "document_id": document_id,
                    "error": str(db_error),
                }, exc_info=True)
            
        except Exception as e:
            logger.error(
                f"Document indexing failed",
                extra={"document_id": document_id, "error": str(e)}
            )
            try:
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(index_status="failed")
                )
                await db.commit()
            except Exception as db_error:
                await db.rollback()
                logger.error("Failed to update document status after general failure", extra={
                    "document_id": document_id,
                    "error": str(db_error),
                }, exc_info=True)

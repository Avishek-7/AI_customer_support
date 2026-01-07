import requests
from .worker import celery_app
from core.config import settings
from core.database import get_sync_db
from models.document import Document


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 20},
)
def index_document_task(self, document_id: int):
    """Background task to index a document via AI engine API.

    Fetches the document from the database so large content isn't serialized
    through the message broker.
    """
    db = get_sync_db()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        response = requests.post(
            f"{settings.AI_ENGINE_URL}/index-document",
            json={
                "document_id": document.id,
                "title": document.title,
                "content": document.content,
            },
            timeout=300,  # 5 minutes for large documents
        )
        response.raise_for_status()
        return response.json()
    finally:
        db.close()


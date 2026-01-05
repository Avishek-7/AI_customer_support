import requests
from .worker import celery_app
from core.config import settings

@celery_app.task(
        bind=True,
        autoretry_for=(Exception,),
        retry_kwargs={"max_retries": 3, "countdown": 15}
)

def index_document_task(self, document_id: int, title: str, content: str):
    """Background task to index a document via AI engine API"""
    try:
        response = requests.post(
            f"{settings.AI_ENGINE_URL}/index-document",
            json={
                "document_id": document_id,
                "title": title,
                "content": content
            },
            timeout=300  # 5 minutes for large documents
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error indexing document {document_id}: {e}")
        raise


from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import uuid

from rag.pipeline import index_document, answer_query, update_document, answer_query_stream
from vectorstore.vector_store import delete_document
from utils.logger import init_logging, get_logger, set_request_id, clear_request_id

# Initialize logging on startup
init_logging()
logger = get_logger("ai_engine.app")

app = FastAPI(
    title="AI Engine - RAG Microservice",
    description="Handles embedding, FAISS reterieval, and LLM generation.",
    version="1.0.0"
)

# Request and Response Models
class IndexDocumentRequest(BaseModel):
    document_id: int
    title: str
    content: str

class IndexDocumentResponse(BaseModel):
    document_id: int
    chunks_indexed: int

class UpdateDocumentResponse(BaseModel):
    document_id: int
    chunks_indexed: int

class UpdateDocumentRequest(BaseModel):
    document_id: int
    title: str
    content: str

class DeleteDocumentRequest(BaseModel):
    document_id: int

class DeleteDocumentResponse(BaseModel):
    document_id: int
    status: str

class QueryRequest(BaseModel):
    session_id: str
    query: str
    system_prompt: Optional[str] = "You are an AI customer support assistant."
    document_ids: Optional[List[int]] = None
    k: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


# Routes

@app.get("/")
def root():
    """Root endpoint - health check"""
    return {
        "status": "AI Engine is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "index": "POST /index-document",
            "query": "POST /query"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai-engine"}

# Index Document
@app.post("/index-document", response_model=IndexDocumentResponse)
async def index_document_endpoint(body: IndexDocumentRequest, background_task: BackgroundTasks):
    """
    Index a new document:
    - chunk the content
    - embed chunks
    - store embeddings + metadata in FAISS 
    """
    req_id = str(uuid.uuid4())[:8]
    set_request_id(req_id)
    
    logger.info(f"Indexing document", extra={
        "document_id": body.document_id,
        "title": body.title,
        "content_length": len(body.content)
    })

    background_task.add_task(
        index_document,
        body.document_id,
        body.title,
        body.content
    )

    # chunks_indexed = await index_document(
    #     document_id=body.document_id,
    #     title=body.title,
    #     content=body.content
    # )

    return IndexDocumentResponse(
        document_id=body.document_id,
        chunks_indexed=0  # indexing still running
    )

# Query RAG Pipeline
@app.post("/query", response_model=QueryResponse)
def query_endpoint(body: QueryRequest):
    """
    Run full RAG pipeline
    - embed query
    - FAISS vector search
    - build prompt with document
    - generate answer using LLM
    """
    req_id = str(uuid.uuid4())[:8]
    set_request_id(req_id)
    
    logger.info("Processing query", extra={
        "query": body.query[:100],
        "session_id": body.session_id,
        "document_ids": body.document_ids,
        "k": body.k
    })

    result = answer_query(
        query=body.query,
        session_id=body.session_id,
        system_prompt=body.system_prompt,
        document_ids=body.document_ids,
        k=body.k,
    )
    
    # Log the full answer for debugging/comparison
    logger.info("=== AI ENGINE ANSWER ===", extra={
        "request_id": req_id,
        "query": body.query,
        "answer": result["answer"],
        "answer_length": len(result["answer"]),
        "sources_count": len(result["sources"])
    })
    logger.info(f"[AI_ENGINE_ANSWER] {result['answer'][:500]}..." if len(result["answer"]) > 500 else f"[AI_ENGINE_ANSWER] {result['answer']}")

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"]
    )

# Update Document
@app.put("/update-document", response_model=IndexDocumentResponse)
def update_document_endpoint(body: IndexDocumentRequest):
    """
    Update an existing document:
    - delete old embeddings
    - re-chunk, re-embed, re-index
    """

    chunks_indexed = update_document(
        document_id=body.document_id,
        title=body.title,
        content=body.content
    )

    return IndexDocumentResponse(
        document_id=body.document_id,
        chunks_indexed=chunks_indexed
    )

# Delete Document
@app.delete("/delete-document/{document_id}", response_model=DeleteDocumentResponse)
def delete_document_endpoint(document_id: int):
    """
    Delete document embeddings from FAISS:
    - removes all chunks for this document_id
    - rebuilds FAISS index
    """
    logger.info(f"Deleting document", extra={"document_id": document_id})
    
    delete_document(document_id)
    
    logger.info(f"Document deleted", extra={"document_id": document_id})
    
    return DeleteDocumentResponse(
        document_id=document_id,
        status="deleted"
    )

@app.post("/stream")
async def stream_answer(body: QueryRequest):
    req_id = str(uuid.uuid4())[:8]
    set_request_id(req_id)
    
    logger.info("Starting stream query", extra={
        "query": body.query[:100],
        "session_id": body.session_id,
        "document_ids": body.document_ids
    })
    
    async def event_generator():
        token_count = 0
        try:
            async for event in answer_query_stream(body):
                if event.get("type") == "token":
                    token_count += 1
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            logger.info(f"Stream completed", extra={"tokens_sent": token_count})
            end_data = {"type": "end"}
            yield f"data: {json.dumps(end_data)}\n\n"
            clear_request_id()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from rag.pipeline import index_document, answer_query, update_document
from vectorstore.vector_store import delete_document

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
def index_document_endpoint(body: IndexDocumentRequest):
    """
    Index a new document:
    - chunk the content
    - embed chunks
    - store embeddings + metadata in FAISS 
    """

    chunks_indexed = index_document(
        document_id=body.document_id,
        title=body.title,
        content=body.content
    )

    return IndexDocumentResponse(
        document_id=body.document_id,
        chunks_indexed=chunks_indexed
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

    result = answer_query(
        query=body.query,
        session_id=body.session_id,
        system_prompt=body.system_prompt,
        document_ids=body.document_ids,
        k=body.k,
    )

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
    
    delete_document(document_id)
    
    return DeleteDocumentResponse(
        document_id=document_id,
        status="deleted"
    )


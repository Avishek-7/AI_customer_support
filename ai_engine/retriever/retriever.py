from typing import List, Optional
from pydantic import Field

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document

from embeddings.embedder import embed_text
from vectorstore.vector_store import search_embeddings
from utils.logger import get_logger

logger = get_logger("ai_engine.retriever")

class FAISSRetriever(BaseRetriever):
    """
    LangChain-compatible Retriever that uses:
    - custome FAISS index (vectorstore/vector_store.py)
    - embedding function (embeddings/embedder.py)
    - Returns LangChain Document objects with metadata

    This integrates LangChain's retriever interface with existing infra.
    """
    
    k: int = Field(default=5, description="Number of documents to retrieve")
    allowed_document_ids: Optional[set] = Field(default=None, description="Optional filter for specific document IDs")

    def __init__(
            self,
            k: int = 5,
            allowed_document_ids: Optional[List[int]] = None,
            **kwargs
    ):
        super().__init__(
            k=k,
            allowed_document_ids=set(allowed_document_ids) if allowed_document_ids else None,
            **kwargs
        )

    def _filter_hits_by_document_ids(self, hits: List[dict]) -> List[dict]:
        if not self.allowed_document_ids:
            return hits
        return [h for h in hits if h.get("document_id") in self.allowed_document_ids]
    
    def _hits_to_documents(self, hits: List[dict]) -> List[Document]:
        docs: List[Document] = []
        for h in hits:
            text = h.get("text", "")
            metadata = {
                "document_id": h.get("document_id"),
                "chunk_id": h.get("chunk_id"),
                "title": h.get("title"),
                "score": h.get("score"),
            }
            docs.append(Document(page_content=text, metadata=metadata))
        return docs
    
    # ---- Synchronous retrieval ----
    def _get_relevant_documents(self, query: str) -> List[Document]:
        logger.info(f"Retrieving documents", extra={
            "query_length": len(query),
            "k": self.k,
            "allowed_document_ids": list(self.allowed_document_ids) if self.allowed_document_ids else None
        })
        
        # 1) embed query
        q_embedding = embed_text(query)

        # 2) search FAISS (over-retrieve a bit) - pass document_ids filter
        hits = search_embeddings(
            q_embedding, 
            k=self.k * 3,
            document_ids=list(self.allowed_document_ids) if self.allowed_document_ids else None
        )

        # 3) keep top-k (already filtered by search_embeddings)
        hits = hits[: self.k]

        # 4) convert to LangChain Documents
        docs = self._hits_to_documents(hits)
        
        logger.info(f"Retrieved documents", extra={"count": len(docs)})
        return docs
    
    # ---- Asynchronous retrieval ----
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        # Just call synchronous version for now
        return self._get_relevant_documents(query)

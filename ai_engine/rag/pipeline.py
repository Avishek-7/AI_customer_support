from typing import List, Dict, Any, Optional
from embeddings.embedder import embed_texts, embed_text
from vectorstore.vector_store import add_embeddings, search_embeddings
from rag.chunker import chunk_text
from llm.llm import generate_answer

# Index Document into FAISS
def index_document(
        document_id: int,
        title: str,
        content: str,
) -> int:
    """
    1) Chunk the document text
    2) Embed the chunks
    3) Store chunk embeddings + metadata in FAISS
    """

    # Step 1: Chunk the document
    chunks = chunk_text(content)
    if not chunks:
        return 0
    
    # Step 2: Embed chunks
    embeddings = embed_texts(chunks)

    # Step 3: Build metadata for each chunk
    metadatas: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        metadatas.append(
            {
                "document_id": document_id,
                "chunk_id": i,
                "title": title,       
                "text": chunk,
            }
        )

    # Step 4: Add to FAISS
    add_embeddings(embeddings, metadatas)

    return len(chunks)

# Answer Query using RAG (Gemini + FAISS)
def answer_query(
        query: str,
        system_prompt: str = "You are an AI customer support assistant.",
        document_ids: Optional[List[int]] = None,
        k: int = 5,
) -> Dict[str, Any]:
    """
    Main RAG pipeline: 
    1) Embed user query
    2) Search FAISS for similar chunks
    3) Optionally filter results by document_ids
    4) Build context
    5) Generate LLM answer
    """

    # Step 1: Embed query
    query_embedding = embed_text(query)

    # Step 2: Search FAISS (over-retrieve for accuracy)
    hits = search_embeddings(query_embedding, k=k*3)

    # Step 3: Optional filtering by user-owned docs
    if document_ids:
        allowed = set(document_ids)
        hits = [h for h in hits if h.get("document_id") in allowed]

    # Keep top-k after filtering
    hits = hits[:k]

    # Extract context text
    context_chunks = [h["text"] for h in hits]

    # Step 5: Generate answer using LLM
    answer = generate_answer(
        question=query,
        context_chunks=context_chunks,
        system_prompt=system_prompt
    )

    # Step 6: Return answer + reterieved sources
    return {
        "answer": answer,
        "sources": hits,
    }
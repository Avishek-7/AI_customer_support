from typing import List, Dict, Any, Optional
from embeddings.embedder import embed_texts, embed_text
from vectorstore.vector_store import add_embeddings, delete_document, search_embeddings
from rag.chunker import chunk_text
from llm.llm import generate_answer, stream_llm_answer
from llm.memory import get_memory, save_turn
from retriever.retriever import FAISSRetriever
from utils.config import settings
import httpx

BACKEND_URL = settings.BACKEND_URL

async def update_status(document_id: int, status: str, chunk_count: int = None):
    """ Notify backend about indexing progress. """
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BACKEND_URL}/api/documents/update-status",
            json={
                "document_id": document_id,
                "status": status,
                "chunk_count": chunk_count,
            }
        )

# Index Document into FAISS
async def index_document(
        document_id: int,
        title: str,
        content: str,
) -> int:
    """
    1) Chunk the document text
    2) Embed the chunks
    3) Store chunk embeddings + metadata in FAISS
    """
    # Step 0: Notify backend
    await update_status(document_id, "processing")

    # Step 1: Chunk the document
    chunks = chunk_text(content)
    await update_status(document_id, "chunking")

    if not chunks:
        await update_status(document_id, "failed")
        return 0
    
    # Step 2: Embed chunks
    embeddings = embed_texts(chunks)
    await update_status(document_id, "embedding")

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
    await update_status(document_id, "saving")

    # Step 5: Completed
    await update_status(document_id, "completed", chunk_count=len(chunks))

    return len(chunks)

# Update Document (Delete + Re-index)
def update_document(
        document_id: int,
        title: str,
        content: str,
) -> int:
    """
    Full update workflow:
    - delete old FAISS entries
    - re-chunk the new content
    - re-embed
    - re-index new embeddings
    """

    # Delete all old chunks for this document
    delete_document(document_id)
    
    # Re-chunk
    chunks = chunk_text(content)
    if not chunks: 
        return 0
    
    # Re-embed
    embeddings = embed_texts(chunks)

    # Re-store into FAISS
    metadatas: List[Dict[str, Any]] =[]
    for idx, chunk in enumerate(chunks):
        metadatas.append(
            {
                "document_id": document_id,
                "chunk_id": idx,
                "title": title,
                "text": chunk,
            }
        )
    add_embeddings(embeddings, metadatas)

    return len(chunks)

# Answer Query using RAG (Gemini + FAISS)
def answer_query(
        query: str,
        session_id: str,
        system_prompt: str = "You are an AI customer support assistant.",
        document_ids: Optional[List[int]] = None,
        k: int = 5,
) -> Dict[str, Any]:
    
    # Get memory for session/user
    memory = get_memory(session_id)
    history = memory.messages  # InMemoryChatHistory stores messages directly

    # LangChain-compatible Retriever
    retriever = FAISSRetriever(
        k=k,
        allowed_document_ids=document_ids,
    )

    # Retrieve relevant chunks (langchain Documents)
    docs = retriever._get_relevant_documents(query)

    # Prepare context for LLM
    context_chunks = [doc.page_content for doc in docs]

    # Render chat history to text for the LLM prompt
    history_text = "\n".join(
        f"User: {m.content}" if getattr(m, "type", "") == "human" else f"Assistant: {getattr(m, 'content', m)}"
        for m in history
    ) if history else ""

    # Call Gemini LLM with RAG context
    answer = generate_answer(
        question=query,
        context_chunks=context_chunks,
        system_prompt=system_prompt,
        chat_history=history_text,
    )

    # Save conversation to memory
    save_turn(session_id, user_message=query, ai_message=answer)

    # Extract metdata for frontend UI
    sources = [doc.metadata for doc in docs]
    return {
        "answer": answer,
        "sources": sources,
    }

async def answer_query_stream(req):
    query = req.query
    k = req.k or 5
    document_ids = req.document_ids

    # Embed query
    query_emb = embed_text(query)

    # Retrieve docs
    results = search_embeddings(query_emb, k=k)
    context_chunks = []
    sources = results
    
    # Stream LLM
    async for token in stream_llm_answer(query, context_chunks, req.system_prompt):
        yield {"type": "token", "content": token}

    # Final event
    yield {
        "type": "final",
        "sources": sources,
        "answer": ""    # frontend will collect tokens into final answer
    }

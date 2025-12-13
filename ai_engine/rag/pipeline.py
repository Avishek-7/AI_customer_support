from typing import List, Dict, Any, Optional
from embeddings.embedder import embed_texts, embed_text
from vectorstore.vector_store import add_embeddings, delete_document, search_embeddings
from rag.chunker import chunk_text
from llm.llm import generate_answer, stream_llm_answer
from llm.memory import get_memory, save_turn
from retriever.retriever import FAISSRetriever
from utils.config import settings
from utils.logger import get_logger
import httpx

logger = get_logger("ai_engine.pipeline")

BACKEND_URL = settings.BACKEND_URL

async def update_status(document_id: int, status: str, chunk_count: int = None):
    """ Notify backend about indexing progress. Non-blocking - failures are logged but don't stop indexing. """
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BACKEND_URL}/documents/update-status",
                json={
                    "document_id": document_id,
                    "status": status,
                    "chunk_count": chunk_count,
                },
                timeout=5.0
            )
            logger.debug(f"Status updated", extra={"document_id": document_id, "status": status})
    except Exception as e:
        logger.warning(f"Could not update status for document {document_id}: {e}")

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
    logger.info(f"Starting document indexing", extra={
        "document_id": document_id,
        "title": title,
        "content_length": len(content)
    })
    
    # Step 0: Notify backend
    await update_status(document_id, "processing")

    # Step 1: Chunk the document
    chunks = chunk_text(content)
    logger.info(f"Document chunked", extra={"document_id": document_id, "chunk_count": len(chunks)})
    await update_status(document_id, "chunking")

    if not chunks:
        logger.error(f"No chunks created for document", extra={"document_id": document_id})
        await update_status(document_id, "failed")
        return 0
    
    # Step 2: Embed chunks
    embeddings = embed_texts(chunks)
    logger.info(f"Chunks embedded", extra={"document_id": document_id, "embedding_shape": embeddings.shape})
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
    logger.info(f"Embeddings added to FAISS", extra={"document_id": document_id})
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
        k: int = 10,  # Retrieve more chunks to ensure complete answers
) -> Dict[str, Any]:
    
    logger.info("Processing RAG query", extra={
        "query": query[:100],
        "session_id": session_id,
        "document_ids": document_ids,
        "k": k
    })
    
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
    logger.info(f"Retrieved {len(docs)} chunks for query")

    # Prepare context for LLM
    raw_chunks = [doc.page_content for doc in docs]
    context_chunks = _prepare_context_list(raw_chunks)

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
    
    # Log the generated answer for debugging/comparison
    logger.info("=== PIPELINE GENERATED ANSWER ===", extra={
        "session_id": session_id,
        "query": query,
        "answer": answer,
        "answer_length": len(answer),
        "sources_count": len(docs)
    })
    logger.info(f"[PIPELINE_ANSWER] {answer[:500]}..." if len(answer) > 500 else f"[PIPELINE_ANSWER] {answer}")

    # Save conversation to memory
    save_turn(session_id, user_message=query, ai_message=answer)

    # Extract metdata for frontend UI
    sources = [doc.metadata for doc in docs]
    
    logger.info("RAG query completed", extra={
        "answer_length": len(answer),
        "sources_count": len(sources)
    })
    
    return {
        "answer": answer,
        "sources": sources,
    }

async def answer_query_stream(req):
    query = req.query
    k = req.k or 10  # Retrieve more chunks to ensure complete answers
    document_ids = req.document_ids

    logger.info("Processing streaming query", extra={
        "query": query[:100],
        "session_id": req.session_id,
        "document_ids": document_ids,
        "k": k
    })

    # Grab chat history for continuity
    memory = get_memory(req.session_id)
    history = memory.messages if memory else []
    history_text = "\n".join(
        f"User: {m.content}" if getattr(m, "type", "") == "human" else f"Assistant: {getattr(m, 'content', m)}"
        for m in history
    ) if history else ""

    # Embed query
    query_emb = embed_text(query)

    # Retrieve docs with document filtering applied at search level
    results = search_embeddings(query_emb, k=k, document_ids=document_ids)
    
    # Remove highly overlapping chunks - keep only chunks with < 50% content overlap
    filtered_results = []
    for i, result in enumerate(results):
        is_redundant = False
        current_text = result.get("text", "").lower()
        
        for existing in filtered_results:
            existing_text = existing.get("text", "").lower()
            # Calculate overlap ratio
            overlap_count = sum(1 for c in current_text if c in existing_text)
            overlap_ratio = overlap_count / len(current_text) if len(current_text) > 0 else 0
            
            if overlap_ratio > 0.5:  # More than 50% overlap = redundant
                is_redundant = True
                break
        
        if not is_redundant:
            filtered_results.append(result)
    
    results = filtered_results
    logger.info(f"Retrieved {len(results)} chunks for streaming query (after dedup)", extra={
        "document_ids": [r.get("document_id") for r in results],
        "chunk_ids": [r.get("chunk_id") for r in results],
        "chunk_titles": [r.get("title", "")[:50] for r in results],
        "chunk_previews": [r.get("text", "")[:80] for r in results]
    })

    # Deduplicate context chunks to avoid repetition
    raw_chunks = [r.get("text", "") for r in results]
    context_chunks = _prepare_context_list(raw_chunks)
    sources = results
    
    # Track full answer for logging and duplicate detection
    full_answer_tokens = []
    full_answer_so_far = ""
    
    # Stream LLM - pass history for better responses
    async for token in stream_llm_answer(query, context_chunks, req.system_prompt, history_text):
        # Skip empty tokens
        if not token:
            continue
        
        # Detect if token would cause repetition (check if this text already appeared)
        if len(full_answer_so_far) > 50:
            # Check if the new token is repeating recent content
            recent_text = full_answer_so_far[-100:]
            if token.strip() and token.strip() in recent_text:
                # Might be starting to repeat, check for longer pattern
                if len(token.strip()) > 3:
                    logger.debug(f"Skipping potentially repeated token: {token[:20]}")
                    continue
        
        full_answer_tokens.append(token)
        full_answer_so_far += token
        yield {"type": "token", "content": token}
    
    # Log the complete streamed answer for debugging/comparison
    full_answer = "".join(full_answer_tokens)
    logger.info("=== PIPELINE STREAMED ANSWER ===", extra={
        "session_id": req.session_id,
        "query": query,
        "answer": full_answer,
        "answer_length": len(full_answer),
        "token_count": len(full_answer_tokens),
        "sources_count": len(sources)
    })
    logger.info(f"[PIPELINE_STREAM_ANSWER] {full_answer[:500]}..." if len(full_answer) > 500 else f"[PIPELINE_STREAM_ANSWER] {full_answer}")

    # Final event with sources
    yield {
        "type": "sources",
        "sources": sources
    }


def _prepare_context_list(chunks: List[str], max_chars: int = 10000) -> List[str]:
    """
    Prepare context chunks for LLM.
    Overlapping chunks have already been filtered in answer_query_stream().
    """
    cleaned_chunks = []
    total_chars = 0

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk or len(chunk) < 20:
            continue

        cleaned_chunks.append(chunk)
        total_chars += len(chunk)
        
        if total_chars > max_chars:
            break
    
    return cleaned_chunks


# def _prepare_context(chunks: List[str], max_chars: int = 3500) -> str:
#     """
#     Deduplicate and trim context to avoid repetition and overload.
#     Returns a joined string for streaming.
#     """
#     return "\n\n".join(_prepare_context_list(chunks, max_chars))
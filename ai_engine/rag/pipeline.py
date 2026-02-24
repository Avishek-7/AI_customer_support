from typing import List, Dict, Any, Optional
from embeddings.embedder import embed_texts, embed_text
from vectorstore.vector_store import add_embeddings, delete_document, search_embeddings, load_index_and_metadata, rebuild_index
from rag.chunker import chunk_text
from llm.llm import generate_answer, stream_llm_answer
from llm.memory import get_memory, save_turn
from retriever.retriever import FAISSRetriever
from retriever.rerank import mmr
from utils.config import get_settings
from utils.metrics import (
    RAG_RETRIEVAL_LATENCY,
    RAG_RERANK_LATENCY,
    LLM_LATENCY,
    RAG_TOTAL_LATENCY,
)
from utils.logger import get_logger
from utils.postprocess import postprocess_answer
from utils.confidence import compute_confidence
from utils.hallucination import detect_hallucination
import httpx
import numpy as np
import time

logger = get_logger("ai_engine.pipeline")
settings = get_settings()

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
                headers={"X-Internal-API-Key": settings.INTERNAL_API_KEY},
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

    await update_status(document_id, "chunking")

    # Step 1: Chunk the document
    chunks = chunk_text(content)
    logger.info(f"Document chunked", extra={"document_id": document_id, "chunk_count": len(chunks)})

    if not chunks:
        logger.error(f"No chunks created for document", extra={"document_id": document_id})
        await update_status(document_id, "failed")
        return 0
    
    try:
        # Step 2: Embed chunks
        await update_status(document_id, "embedding")
        embeddings = embed_texts(chunks)
        logger.info(f"Chunks embedded", extra={"document_id": document_id, "embedding_shape": embeddings.shape})

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
    except Exception as e:
        logger.error("Indexing failed during embedding/save", extra={
            "document_id": document_id,
            "error": str(e)
        }, exc_info=True)
        await update_status(document_id, "failed")
        raise

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

    logger.info("Starting document update", extra={
        "document_id": document_id,
        "title": title,
        "content_length": len(content),
    })

    _, existing_metadata = load_index_and_metadata()
    old_document_metadata = [m.copy() for m in existing_metadata if m.get("document_id") == document_id]

    try:
        delete_document(document_id)
        logger.info("Deleted existing document chunks", extra={"document_id": document_id})

        chunks = chunk_text(content)
        if not chunks:
            logger.warning("No chunks created during update", extra={"document_id": document_id})
            return 0

        embeddings = embed_texts(chunks)
        logger.info("Embedded updated chunks", extra={"document_id": document_id, "chunk_count": len(chunks)})

        metadatas: List[Dict[str, Any]] = []
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
        logger.info("Document update completed", extra={"document_id": document_id, "chunk_count": len(chunks)})
        return len(chunks)
    except Exception as e:
        logger.error("Document update failed", extra={
            "document_id": document_id,
            "error": str(e),
        }, exc_info=True)

        if old_document_metadata:
            logger.warning("Restoring previous document vectors after update failure", extra={"document_id": document_id})
            _, current_metadata = load_index_and_metadata()
            without_document = [m for m in current_metadata if m.get("document_id") != document_id]
            rebuild_index(without_document + old_document_metadata)

        raise

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

    total_start = time.perf_counter()
    
    # Get memory for session/user
    memory = get_memory(session_id)
    history = memory.messages if memory else []

    # LangChain-compatible Retriever
    retriever = FAISSRetriever(
        k=k,
        allowed_document_ids=document_ids,
    )

    # Retrieve relevant chunks (langchain Documents)
    retrieval_start = time.perf_counter()
    docs = retriever._get_relevant_documents(query)
    retrieval_duration = time.perf_counter() - retrieval_start
    RAG_RETRIEVAL_LATENCY.labels("sync").observe(retrieval_duration)
    logger.info(f"Retrieved {len(docs)} chunks for query")

    # Apply MMR reranking for better diversity (optional)
    if settings.ENABLE_MMR_RERANK and len(docs) > 1:
        rerank_start = time.perf_counter()
        query_emb = embed_text(query)
        doc_texts = [doc.page_content for doc in docs]
        doc_embs = embed_texts(doc_texts)

        top_k = min(k, len(docs))
        reranked_indices = mmr(query_emb, doc_embs, lambda_param=0.7, top_k=top_k)
        docs = [docs[i] for i in reranked_indices]
        rerank_duration = time.perf_counter() - rerank_start
        RAG_RERANK_LATENCY.labels("sync").observe(rerank_duration)
        logger.info(f"Applied MMR reranking, using top {len(docs)} diverse chunks")
    else:
        RAG_RERANK_LATENCY.labels("sync").observe(0)

    # Prepare context for LLM
    raw_chunks = [doc.page_content for doc in docs]
    context_chunks = _prepare_context_list(raw_chunks)

    # Render chat history to text for the LLM prompt
    history_text = "\n".join(
        f"User: {m.content}" if getattr(m, "type", "") == "human" else f"Assistant: {getattr(m, 'content', m)}"
        for m in history
    ) if history else ""

    # Call Gemini LLM with RAG context
    llm_start = time.perf_counter()
    answer = generate_answer(
        question=query,
        context_chunks=context_chunks,
        system_prompt=system_prompt,
        chat_history=history_text,
    )
    llm_duration = time.perf_counter() - llm_start
    LLM_LATENCY.labels("sync").observe(llm_duration)
    
    # Postprocess the answer to clean up formatting and remove repetitions
    answer = postprocess_answer(answer)
    
    # Log the generated answer for debugging/comparison
    logger.info("=== PIPELINE GENERATED ANSWER ===", extra={
        "session_id": session_id,
        "query_preview": query[:120],
        "answer_preview": answer[:200],
        "answer_length": len(answer),
        "sources_count": len(docs)
    })

    # Save conversation to memory
    save_turn(session_id, user_message=query, ai_message=answer)

    # Extract metadata for frontend UI
    sources = [doc.metadata for doc in docs]
    
    logger.info("RAG query completed", extra={
        "answer_length": len(answer),
        "sources_count": len(sources)
    })

    total_duration = time.perf_counter() - total_start
    RAG_TOTAL_LATENCY.labels("sync").observe(total_duration)
    logger.info("RAG timing", extra={
        "retrieval_ms": round(retrieval_duration * 1000, 2),
        "llm_ms": round(llm_duration * 1000, 2),
        "total_ms": round(total_duration * 1000, 2)
    })

    confidence = compute_confidence(sources, answer)
    logger.info("Computed answer confidence", extra={
        "confidence": confidence,
        "answer_length": len(answer),
        "sources_count": len(sources)
    })
    
    # Detect potential hallucinations
    hallucination_result = detect_hallucination(answer, sources)
    logger.info("Hallucination detection completed", extra={
        "hallucination_score": hallucination_result.get("hallucination_score"),
        "alignment_score": hallucination_result.get("alignment_score"),
        "risk_level": hallucination_result.get("details", {}).get("risk_level")
    })
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "hallucination_detection": hallucination_result
    }

async def answer_query_stream(req):
    query = req.query
    k = req.k if req.k is not None else 10  # Retrieve more chunks to ensure complete answers
    document_ids = req.document_ids

    logger.info("Processing streaming query", extra={
        "query": query[:100],
        "session_id": req.session_id,
        "document_ids": document_ids,
        "k": k
    })

    total_start = time.perf_counter()

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
    retrieval_start = time.perf_counter()
    results = search_embeddings(query_emb, k=k, document_ids=document_ids)
    retrieval_duration = time.perf_counter() - retrieval_start
    RAG_RETRIEVAL_LATENCY.labels("stream").observe(retrieval_duration)

    logger.info(f"FAISS search returned {len(results)} chunks BEFORE dedup", extra={
        "document_ids_in_results": [r.get("document_id") for r in results],
        "filter_document_ids": document_ids
    })

    # Only remove exact or near-exact duplicate chunks within the same document
    # Different documents can have similar structure, so preserve cross-document chunks
    filtered_results = []
    seen_chunks = {}  # key: (doc_id, text_hash), value: text

    for result in results:
        doc_id = result.get("document_id")
        chunk_content = result.get("text", "").strip()

        # Skip if this exact chunk from same document was already seen
        chunk_key = (doc_id, hash(chunk_content))
        if chunk_key in seen_chunks:
            logger.debug(f"Skipping exact duplicate chunk from document {doc_id}")
            continue

        filtered_results.append(result)
        seen_chunks[chunk_key] = chunk_content

    results = filtered_results
    logger.info(f"Retrieved {len(results)} chunks for streaming query (after dedup)", extra={
        "document_ids": [r.get("document_id") for r in results],
        "chunk_ids": [r.get("chunk_id") for r in results],
        "chunk_titles": [r.get("title", "")[:50] for r in results],
        "chunk_previews": [r.get("text", "")[:80] for r in results]
    })

    # Apply MMR reranking for better diversity (optional)
    if settings.ENABLE_MMR_RERANK and len(results) > 1:
        rerank_start = time.perf_counter()
        result_texts = [r.get("text", "") for r in results]
        result_embs = embed_texts(result_texts)

        top_k = min(k, len(results))
        reranked_indices = mmr(query_emb, result_embs, lambda_param=0.7, top_k=top_k)
        results = [results[i] for i in reranked_indices]
        rerank_duration = time.perf_counter() - rerank_start
        RAG_RERANK_LATENCY.labels("stream").observe(rerank_duration)
        logger.info(f"Applied MMR reranking, using top {len(results)} diverse chunks")
    else:
        RAG_RERANK_LATENCY.labels("stream").observe(0)

    # Deduplicate context chunks to avoid repetition
    raw_chunks = [r.get("text", "") for r in results]
    context_chunks = _prepare_context_list(raw_chunks)
    sources = results

    # Track full answer for postprocessing
    full_answer_tokens = []

    # Stream LLM - pass history for better responses
    llm_start = time.perf_counter()
    async for token in stream_llm_answer(query, context_chunks, req.system_prompt, history_text):
        if not token:
            continue
        full_answer_tokens.append(token)
        yield {"type": "token", "content": token}

    llm_duration = time.perf_counter() - llm_start
    LLM_LATENCY.labels("stream").observe(llm_duration)

    total_duration = time.perf_counter() - total_start
    RAG_TOTAL_LATENCY.labels("stream").observe(total_duration)
    logger.info("RAG streaming timing", extra={
        "retrieval_ms": round(retrieval_duration * 1000, 2),
        "llm_ms": round(llm_duration * 1000, 2),
        "total_ms": round(total_duration * 1000, 2)
    })
    
    # Postprocess final answer for persistence/analytics (stream already emitted incrementally)
    full_answer = postprocess_answer("".join(full_answer_tokens))
    
    logger.info("=== PIPELINE STREAMED ANSWER ===", extra={
        "session_id": req.session_id,
        "query_preview": query[:120],
        "answer_preview": full_answer[:200],
        "answer_length": len(full_answer),
        "token_count": len(full_answer_tokens),
        "sources_count": len(sources)
    })

    # Save conversation to memory for chat history continuity
    save_turn(req.session_id, user_message=query, ai_message=full_answer)

    # Compute confidence score
    confidence = compute_confidence(sources, full_answer)
    logger.info("Computed answer confidence", extra={
        "confidence": confidence,
        "answer_length": len(full_answer),
        "sources_count": len(sources)
    })
    
    # Detect potential hallucinations
    hallucination_result = detect_hallucination(full_answer, sources)
    logger.info("Hallucination detection completed", extra={
        "hallucination_score": hallucination_result.get("hallucination_score"),
        "alignment_score": hallucination_result.get("alignment_score"),
        "risk_level": hallucination_result.get("details", {}).get("risk_level")
    })

    # Final event with sources, confidence, and hallucination detection
    yield {
        "type": "sources",
        "sources": sources,
        "confidence": confidence,
        "hallucination_detection": hallucination_result
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

        prospective_size = total_chars + len(chunk)
        if prospective_size > max_chars:
            remaining = max_chars - total_chars
            if remaining <= 0:
                break
            truncated = chunk[:remaining].strip()
            if truncated:
                cleaned_chunks.append(truncated)
                total_chars += len(truncated)
            break

        cleaned_chunks.append(chunk)
        total_chars = prospective_size
    
    return cleaned_chunks


# def _prepare_context(chunks: List[str], max_chars: int = 3500) -> str:
#     """
#     Deduplicate and trim context to avoid repetition and overload.
#     Returns a joined string for streaming.
#     """
#     return "\n\n".join(_prepare_context_list(chunks, max_chars))
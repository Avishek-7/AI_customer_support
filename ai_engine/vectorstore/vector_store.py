import os
import json
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import faiss
from embeddings.embedder import EMBEDDING_DIM
from utils.logger import get_logger

logger = get_logger("ai_engine.vectorstore")

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "faiss_index.bin")
META_PATH = os.path.join(DATA_DIR, "metadata.json")

os.makedirs(DATA_DIR, exist_ok=True)

# Load / Create Index
def _empty_index() -> faiss.IndexFlatL2:
    """
    Create a new empty FAISS index.
    """
    return faiss.IndexFlatL2(EMBEDDING_DIM)

def load_index_and_metadata() -> Tuple[faiss.IndexFlatL2, List[Dict[str, Any]]]:
    """
    Load FAISS index + metadata, or initialize if missing.
    """

    # Load metadata (list of dicts)
    if os.path.exists(META_PATH):
        with open(META_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = []

    # Load index
    if os.path.exists(INDEX_PATH):
        index = faiss.read_index(INDEX_PATH)
    else:
        index = _empty_index()

    # Safety check (FAISS count must match metadata count)
    if index.ntotal != len(metadata):
        index = _empty_index()
        metadata = []

    return index, metadata


# Save Index and Metadata
def save_index_and_metadata(index: faiss.IndexFlatL2, metadata: List[Dict[str, Any]]) -> None:
    """
    Save FAISS index + JSON metadata
    """
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


# Add Embeddings
def add_embeddings(embeddings: np.ndarray, metadatas: List[Dict[str, Any]]) -> None:
    """
    Add embeddings + metadata to the FAISS index.
    embeddings: shape (N, EMBEDDING_DIM)
    metadatas: list of dicts of length N
    """
    logger.info(f"Adding embeddings to FAISS", extra={
        "count": len(metadatas),
        "embedding_shape": embeddings.shape
    })
    
    index, metadata = load_index_and_metadata()

    if embeddings.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            f"Embedding dimension mismatch: got {embeddings.shape[1]}, expected {EMBEDDING_DIM}"   
        )
    
    index.add(embeddings)
    metadata.extend(metadatas)
    save_index_and_metadata(index, metadata)
    
    logger.info(f"FAISS index updated", extra={"total_vectors": index.ntotal})

# Delete all chunks of a single document
def delete_document(document_id: int) -> None:
    """
    Delete all FAISS vectors belonging to a document.
    Rebuilds FAISS index by re-embedding remaining documents.
    """
    logger.info(f"Deleting document from FAISS", extra={"document_id": document_id})
    
    from embeddings.embedder import embed_texts
    
    index, metadata = load_index_and_metadata()

    # Filter out metadata for this document
    new_metadata = [m for m in metadata if m["document_id"] != document_id]

    # If nothing changed, do nothing
    if len(new_metadata) == len(metadata):
        logger.info(f"No chunks found for document, nothing to delete", extra={"document_id": document_id})
        return
    
    chunks_removed = len(metadata) - len(new_metadata)
    logger.info(f"Removed chunks, rebuilding index", extra={
        "document_id": document_id,
        "chunks_removed": chunks_removed,
        "remaining_chunks": len(new_metadata)
    })
    
    # Rebuild FAISS from scratch by re-embedding
    rebuild_index(new_metadata)

# Rebuild FAISS Index (used after deletion and updates)
def rebuild_index(metadata: List[Dict[str, Any]]) -> None:
    """
    Rebuild FAISS index from metadata by re-embedding text content.
    This is necessary because embeddings are stored in FAISS, not metadata.
    """
    logger.info(f"Rebuilding FAISS index", extra={"metadata_count": len(metadata)})
    
    from embeddings.embedder import embed_texts
    
    new_index = _empty_index()

    if len(metadata) > 0:
        # Extract text from metadata and re-embed
        texts = [m["text"] for m in metadata]
        embeddings = embed_texts(texts)
        new_index.add(embeddings)

    save_index_and_metadata(new_index, metadata)
    logger.info(f"FAISS index rebuilt successfully", extra={"total_vectors": new_index.ntotal})


# Search
def search_embeddings(
    query_embedding: np.ndarray, 
    k: int = 5,
    document_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Search FAISS index. Returns list of metadata dicts with added score.
    Optionally filter by document_ids.
    
    For queries about sections/metrics, also includes related section keywords.
    """
    logger.info(f"Searching FAISS index", extra={
        "k": k,
        "document_ids_filter": document_ids
    })
    
    index, metadata = load_index_and_metadata()
    
    if index.ntotal == 0:
        logger.warning("FAISS index is empty, returning no results")
        return []
    
    # Log what document IDs exist in FAISS for debugging
    existing_doc_ids = list(set(m.get("document_id") for m in metadata))
    logger.info(f"FAISS contains document IDs: {existing_doc_ids}")
    
    if document_ids:
        matching_ids = [d for d in document_ids if d in existing_doc_ids]
        if not matching_ids:
            logger.warning(f"No matching document IDs! Requested: {document_ids}, Available: {existing_doc_ids}")
        else:
            logger.info(f"Filtering to document IDs: {matching_ids}")
    
    query_embedding = query_embedding.reshape(1, -1).astype("float32")

    # If filtering, retrieve more candidates to ensure we get enough after filtering
    search_k = k * 5 if document_ids else k * 2  # Retrieve more candidates
    search_k = min(search_k, index.ntotal)  # Don't exceed total docs
    
    distances, indices = index.search(query_embedding, search_k)

    results = []
    results_dict = {}  # Track by chunk to deduplicate
    
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue

        item = metadata[idx].copy()
        
        # Filter by document_ids if specified
        if document_ids and item.get("document_id") not in document_ids:
            continue
        
        # Boost score if chunk contains section headers relevant to queries about "evaluation metrics"
        chunk_text = item.get("text", "").lower()
        boost = 0
        if any(keyword in chunk_text for keyword in ["evaluation metrics:", "code:", "database:", "logging:", "deployment:", "optimization:"]):
            boost = -0.1  # Lower distance = better, so negative boost improves score
        
        item["score"] = float(dist) + boost
        
        # Use chunk_id as key to avoid duplicates
        chunk_key = (item.get("document_id"), item.get("chunk_id"))
        if chunk_key not in results_dict:
            results_dict[chunk_key] = item
            results.append(item)
        
        # Stop once we have enough results
        if len(results) >= k:
            break

    # Sort by score (lower is better for L2 distance)
    results.sort(key=lambda x: x["score"])
    results = results[:k]

    logger.info(f"FAISS search completed", extra={
        "results_count": len(results),
        "index_total": index.ntotal,
        "scores": [round(r["score"], 3) for r in results]
    })
    
    return results
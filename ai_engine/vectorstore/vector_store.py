import os
import json
from typing import List, Dict, Any, Tuple
import numpy as np
import faiss
from embeddings.embedder import EMBEDDING_DIM

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
    index, metadata = load_index_and_metadata()

    if embeddings.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            f"Embedding dimension mismatch: got {embeddings.shape[1]}, expected {EMBEDDING_DIM}"   
        )
    
    index.add(embeddings)
    metadata.extend(metadatas)
    save_index_and_metadata(index, metadata)


# Search
def search_embeddings(query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search FAISS index. Returns list of metadata dicts with added score.
    """
    index, metadata = load_index_and_metadata()
    
    if index.ntotal == 0:
        return []
    
    query_embedding = query_embedding.reshape(1, -1).astype("float32")

    distances, indices = index.search(query_embedding, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue

        item = metadata[idx].copy()
        item["score"] = float(dist)
        results.append(item)

    return results
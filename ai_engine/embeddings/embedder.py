from functools import lru_cache
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # Dimension for all-MiniLM-L6-v2

@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Lazy-load and cache the model (loads only once). 
    """
    return SentenceTransformer(MODEL_NAME)

def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Embed multiple text cuhunks into 2D numpy array.
    Returns shape: (num_texts, EMBEDDING_DIM) 
    """
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False
    )
    return embeddings.astype("float32")

def embed_text(text: str) -> np.ndarray:
    """
    Embed a single piece of text into a 1D numpy array.
    """
    return embed_texts([text])[0]


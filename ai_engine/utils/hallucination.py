import re
from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from embeddings.embedder import embed_text, embed_texts


def detect_hallucination(answer: str, sources: List[dict]) -> dict:
    """
    Detect potential hallucinations by scoring answer alignment with sources.
    
    Returns:
        dict with hallucination_score (0-1, lower is better), 
        alignment_score (0-1, higher is better),
        and details about the scoring
    """
    if not answer or not sources:
        return {
            "hallucination_score": 0.0,
            "alignment_score": 0.0,
            "details": {
                "reason": "No answer or sources to compare",
                "risk_level": "low"
            }
        }
    
    # Extract source texts
    source_texts = [s.get("text", "") for s in sources if s.get("text")]
    if not source_texts:
        return {
            "hallucination_score": 0.9,  # High hallucination risk if no sources
            "alignment_score": 0.1,
            "details": {
                "reason": "No source texts available",
                "risk_level": "high"
            }
        }
    
    # 1. Embedding-based similarity
    answer_emb = embed_text(answer)
    source_embs = embed_texts(source_texts)
    
    # Compute similarity between answer and each source
    similarities = cosine_similarity([answer_emb], source_embs)[0]
    max_similarity = float(np.max(similarities))
    avg_similarity = float(np.mean(similarities))
    
    # 2. Keyword overlap scoring
    answer_words = set(re.findall(r'\w+', answer.lower()))
    source_words = set()
    for text in source_texts:
        source_words.update(re.findall(r'\w+', text.lower()))
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'}
    answer_words -= stop_words
    source_words -= stop_words
    
    if answer_words:
        keyword_overlap = len(answer_words & source_words) / len(answer_words)
    else:
        keyword_overlap = 0.0
    
    # 3. Combined alignment score (weighted average)
    # Higher weight on embedding similarity as it captures semantic meaning
    alignment_score = (0.6 * max_similarity + 0.3 * avg_similarity + 0.1 * keyword_overlap)
    
    # Hallucination score is inverse of alignment (low alignment = high hallucination risk)
    hallucination_score = 1.0 - alignment_score
    
    return {
        "hallucination_score": round(hallucination_score, 3),
        "alignment_score": round(alignment_score, 3),
        "details": {
            "max_source_similarity": round(max_similarity, 3),
            "avg_source_similarity": round(avg_similarity, 3),
            "keyword_overlap": round(keyword_overlap, 3),
            "num_sources": len(sources),
            "answer_length": len(answer),
            "risk_level": _get_risk_level(hallucination_score)
        }
    }


def _get_risk_level(hallucination_score: float) -> str:
    """Convert hallucination score to human-readable risk level."""
    if hallucination_score < 0.3:
        return "low"
    elif hallucination_score < 0.6:
        return "medium"
    else:
        return "high"

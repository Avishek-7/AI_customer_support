def compute_confidence(sources: list, answer: str) -> float:
    if not sources or not answer:
        return 0.2
    
    # Average FAISS distance -> similarity proxy
    scores = [1 / (1 + s.get("score", 1.0)) for s in sources]
    avg_relevance = sum(scores) / len(scores)

    # Penalize overly short answers
    length_factor = min(len(answer) / 300, 10)

    confidence = 0.6 * avg_relevance + 0.4 * length_factor
    return round(min(confidence, 0.95), 2)
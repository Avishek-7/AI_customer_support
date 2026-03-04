import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def mmr(query_emb, doc_embs, lambda_param=0.5, top_k=5):
    if doc_embs is None or len(doc_embs) == 0:
        raise ValueError("doc_embs must be non-empty")

    if not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")

    if not (0.0 <= lambda_param <= 1.0):
        raise ValueError("lambda_param must be within [0, 1]")

    doc_embs_arr = np.asarray(doc_embs)
    query_emb_arr = np.asarray(query_emb)

    if doc_embs_arr.ndim != 2:
        raise ValueError("doc_embs must be a 2D array-like structure")

    if query_emb_arr.ndim == 1:
        if query_emb_arr.shape[0] != doc_embs_arr.shape[1]:
            raise ValueError("query_emb dimension must match doc_embs embedding dimension")
    elif query_emb_arr.ndim == 2 and query_emb_arr.shape[0] == 1:
        if query_emb_arr.shape[1] != doc_embs_arr.shape[1]:
            raise ValueError("query_emb dimension must match doc_embs embedding dimension")
        query_emb_arr = query_emb_arr[0]
    else:
        raise ValueError("query_emb must be a 1D embedding vector")

    top_k = min(top_k, len(doc_embs_arr))

    selected = []
    candidates = list(range(len(doc_embs_arr)))

    sim_query = cosine_similarity([query_emb_arr], doc_embs_arr)[0]
    sim_docs = cosine_similarity(doc_embs_arr)

    for _ in range(top_k):
        mmr_score = []
        for i in candidates:
            diversity = max([sim_docs[i][j] for j in selected], default=0)
            score = lambda_param * sim_query[i] - (1 - lambda_param) * diversity
            mmr_score.append((score, i))

        _, best = max(mmr_score)
        selected.append(best)
        candidates.remove(best)
    
    return selected
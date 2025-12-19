import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def mmr(query_emb, doc_embs, lambda_param=0.5, top_k=5):
    selected = []
    candidates = list(range(len(doc_embs)))

    sim_query = cosine_similarity([query_emb], doc_embs)[0]
    sim_docs = cosine_similarity(doc_embs)

    for _ in range(min(top_k, len(doc_embs))):
        mmr_score = []
        for i in candidates:
            diversity = max([sim_docs[i][j] for j in selected], default=0)
            score = lambda_param * sim_query[i] - (1 - lambda_param) * diversity
            mmr_score.append((score, i))

        _, best = max(mmr_score)
        selected.append(best)
        candidates.remove(best)
    
    return selected
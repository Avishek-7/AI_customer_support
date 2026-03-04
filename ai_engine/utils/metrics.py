from prometheus_client import Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUEST_LATENCY = Histogram(
    "ai_engine_request_latency_seconds",
    "AI engine request latency in seconds",
    ["route", "method", "status"],
)

RAG_RETRIEVAL_LATENCY = Histogram(
    "ai_engine_rag_retrieval_seconds",
    "RAG retrieval latency in seconds",
    ["mode"],
)

RAG_RERANK_LATENCY = Histogram(
    "ai_engine_rag_rerank_seconds",
    "RAG rerank latency in seconds",
    ["mode"],
)

LLM_LATENCY = Histogram(
    "ai_engine_llm_latency_seconds",
    "LLM generation latency in seconds",
    ["mode"],
)

RAG_TOTAL_LATENCY = Histogram(
    "ai_engine_rag_total_seconds",
    "RAG total latency in seconds",
    ["mode"],
)


def render_metrics():
    return generate_latest(), CONTENT_TYPE_LATEST

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUEST_LATENCY = Histogram(
    "backend_request_latency_seconds",
    "Backend request latency in seconds",
    ["path", "method", "status"],
)

AI_ENGINE_LATENCY = Histogram(
    "backend_ai_engine_latency_seconds",
    "Latency of AI engine calls in seconds",
    ["endpoint"],
)

CACHE_HITS = Counter(
    "backend_chat_cache_hits_total",
    "Total chat cache hits",
    ["endpoint"],
)

CACHE_MISSES = Counter(
    "backend_chat_cache_misses_total",
    "Total chat cache misses",
    ["endpoint"],
)


def render_metrics():
    return generate_latest(), CONTENT_TYPE_LATEST

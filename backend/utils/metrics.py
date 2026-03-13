from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

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

RATE_LIMIT_REDIS_DEGRADED = Gauge(
    "backend_rate_limit_redis_degraded",
    "1 when Redis-backed rate limiting is degraded or unavailable",
)

RATE_LIMIT_FAIL_CLOSED_TOTAL = Counter(
    "backend_rate_limit_fail_closed_total",
    "Total requests denied because rate limiting failed closed",
    ["reason"],
)

RATE_LIMIT_IN_MEMORY_FALLBACK_TOTAL = Counter(
    "backend_rate_limit_in_memory_fallback_total",
    "Total requests handled by in-memory rate limiting fallback",
    ["reason"],
)


def render_metrics():
    return generate_latest(), CONTENT_TYPE_LATEST

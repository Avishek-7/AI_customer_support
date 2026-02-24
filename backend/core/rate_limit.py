import time
import threading
from redis import Redis
from fastapi import HTTPException
from utils.logger import get_logger
from core.error_handler import ErrorHandler
from core.config import settings

logger = get_logger("backend.core.rate_limit")

# Initialize Redis with connection pool
try:
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=2,
    )
    # Test connection
    redis.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis connection established for rate limiting")
except Exception as e:
    REDIS_AVAILABLE = False
    redis = None
    logger.warning(f"Redis not available - using in-memory limiter fallback: {e}")

_IN_MEMORY_LIMITS = {}
_IN_MEMORY_LIMITS_LOCK = threading.Lock()
_REDIS_FAIL_COUNT = 0
_REDIS_CIRCUIT_OPEN_UNTIL = 0.0
_REDIS_CIRCUIT_LOCK = threading.Lock()
_REDIS_CIRCUIT_THRESHOLD = 3
_REDIS_CIRCUIT_SECONDS = 30

_ATOMIC_INCR_EXPIRE_SCRIPT = None
if REDIS_AVAILABLE and redis is not None:
    try:
        _ATOMIC_INCR_EXPIRE_SCRIPT = redis.register_script(
            """
            local current = redis.call('INCR', KEYS[1])
            if current == 1 then
                redis.call('EXPIRE', KEYS[1], ARGV[1])
            end
            return current
            """
        )
    except Exception as e:
        logger.warning(f"Failed to register Redis rate-limit script: {e}")
        _ATOMIC_INCR_EXPIRE_SCRIPT = None


def _in_memory_rate_limit(key: str, limit: int, window: int):
    """Thread-safe in-memory fallback rate limiter."""
    now = time.time()
    with _IN_MEMORY_LIMITS_LOCK:
        expired_keys = [k for k, v in _IN_MEMORY_LIMITS.items() if now >= v["expires_at"]]
        for expired_key in expired_keys:
            del _IN_MEMORY_LIMITS[expired_key]

        state = _IN_MEMORY_LIMITS.get(key)
        if state is None:
            _IN_MEMORY_LIMITS[key] = {"count": 1, "expires_at": now + window}
            count = 1
        else:
            state["count"] += 1
            count = state["count"]

    if count > limit:
        logger.warning(f"In-memory rate limit exceeded", extra={"key": key, "count": count, "limit": limit})
        raise ErrorHandler.rate_limited("You have exceeded the rate limit. Please try again later.")


def rate_limit_key(key: str, limit=100, window=60):
    """
    Rate limit requests by an arbitrary key.
    Uses Redis atomic INCR+EXPIRE when available, otherwise in-memory fallback.
    """
    global _REDIS_FAIL_COUNT, _REDIS_CIRCUIT_OPEN_UNTIL

    now = time.time()
    with _REDIS_CIRCUIT_LOCK:
        circuit_open_until = _REDIS_CIRCUIT_OPEN_UNTIL

    if (not REDIS_AVAILABLE or redis is None) or now < circuit_open_until:
        if now < circuit_open_until:
            logger.warning("Redis circuit breaker open, using in-memory limiter", extra={"key": key})
        try:
            _in_memory_rate_limit(key=key, limit=limit, window=window)
            return
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"In-memory rate limiter failure: {e}", extra={"key": key})
            raise ErrorHandler.service_unavailable("Rate limiting service temporarily unavailable")

    try:
        if _ATOMIC_INCR_EXPIRE_SCRIPT is not None:
            count = int(_ATOMIC_INCR_EXPIRE_SCRIPT(keys=[key], args=[window]))
        else:
            # Fallback path if script registration failed
            pipeline = redis.pipeline(transaction=True)
            pipeline.incr(key)
            pipeline.expire(key, window)
            results = pipeline.execute()
            count = int(results[0])

        if count > limit:
            logger.warning(f"Rate limit exceeded", extra={"key": key, "count": count, "limit": limit})
            raise ErrorHandler.rate_limited("You have exceeded the rate limit. Please try again later.")

        with _REDIS_CIRCUIT_LOCK:
            _REDIS_FAIL_COUNT = 0
            _REDIS_CIRCUIT_OPEN_UNTIL = 0.0
    except HTTPException:
        raise
    except Exception as e:
        opened_circuit = False
        with _REDIS_CIRCUIT_LOCK:
            _REDIS_FAIL_COUNT += 1
            failure_count = _REDIS_FAIL_COUNT
            if _REDIS_FAIL_COUNT >= _REDIS_CIRCUIT_THRESHOLD:
                _REDIS_CIRCUIT_OPEN_UNTIL = time.time() + _REDIS_CIRCUIT_SECONDS
                opened_circuit = True

        if opened_circuit:
            logger.warning("Opening Redis rate-limit circuit breaker", extra={
                "open_seconds": _REDIS_CIRCUIT_SECONDS,
                "failure_count": failure_count,
            })

        logger.error(f"Rate limit check failed: {e}", extra={"key": key})
        try:
            _in_memory_rate_limit(key=key, limit=limit, window=window)
        except HTTPException:
            raise
        except Exception as fallback_error:
            logger.error(f"In-memory fallback limiter failure: {fallback_error}", extra={"key": key})
            raise ErrorHandler.service_unavailable("Rate limiting service temporarily unavailable")

def rate_limit(user_id: str | int, limit=100, window=60):
    """
    Rate limit requests per identifier.
    """
    rate_limit_key(key=f"rate:{user_id}", limit=limit, window=window)
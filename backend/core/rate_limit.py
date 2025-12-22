import time
from redis import Redis
from fastapi import HTTPException
from utils.logger import get_logger

logger = get_logger("backend.core.rate_limit")

# Initialize Redis with connection pool
try:
    redis = Redis(host="localhost", port=6379, decode_responses=True, socket_connect_timeout=1)
    # Test connection
    redis.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis connection established for rate limiting")
except Exception as e:
    REDIS_AVAILABLE = False
    redis = None
    logger.warning(f"Redis not available - rate limiting disabled: {e}")

def rate_limit(user_id: int, limit=100, window=60):
    """
    Rate limit requests per user.
    If Redis is not available, this function becomes a no-op (graceful degradation).
    """
    if not REDIS_AVAILABLE or redis is None:
        # Gracefully degrade - log warning but don't block requests
        logger.debug(f"Rate limit check skipped (Redis unavailable) for user {user_id}")
        return
    
    try:
        key = f"rate:{user_id}"
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, window)
        if count > limit:
            logger.warning(f"Rate limit exceeded", extra={"user_id": user_id, "count": count, "limit": limit})
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except HTTPException:
        # Re-raise HTTP exceptions (actual rate limit violations)
        raise
    except Exception as e:
        # Log error but don't block the request
        logger.error(f"Rate limit check failed: {e}", extra={"user_id": user_id})
        # Graceful degradation - allow request to proceed
    
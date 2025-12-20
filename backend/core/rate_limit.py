import time
from redis import Redis
from fastapi import HTTPException

redis = Redis()

def rate_limit(user_id: int, limit=100, window=60):
    key = f"rate:{user_id}"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, window)
    if count > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
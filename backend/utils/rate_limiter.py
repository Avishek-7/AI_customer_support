import time
from fastapi import HTTPException, status

# Store request timestamps per user in memory (simple and fast)
# Example: {
#   "user_id_1": [timestamp1, timestamp2, ...],
#   "user_id_2": [timestamp1, timestamp2, ...],
#}
request_logs = {}

def rate_limit(user_id: str, limit: int = 20, per_seconds: int = 60):
    now = time.time()
    user_requests = request_logs.get(user_id, [])

    # Filter out old requests 
    user_requests = [t for t in user_requests if now -t < per_seconds]

    # Save new filtered requests
    request_logs[user_id] = user_requests

    if len(user_requests) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Limit is {limit} per {per_seconds} seconds."
        )
    
    # Add current timestamp
    request_logs[user_id].append(now)

    
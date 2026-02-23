from models.usage import APIUsage
import importlib
from utils.logger import get_logger

logger = get_logger("backend.utils.usage_tracker")


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    if not text:
        return 0

    tiktoken = importlib.import_module("tiktoken")

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))

async def track_usage(db, user_id, endpoint, tokens, latency):
    db.add(APIUsage(
        user_id=user_id,
        endpoint=endpoint,
        tokens=tokens,
        latency=latency  
    ))

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Failed to commit API usage", extra={
            "user_id": user_id,
            "endpoint": endpoint,
            "error": str(e),
        })
        raise
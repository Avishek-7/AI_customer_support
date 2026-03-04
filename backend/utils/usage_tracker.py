from models.usage import APIUsage
import importlib
import hashlib
from utils.logger import get_logger

logger = get_logger("backend.utils.usage_tracker")


def _anonymize_user_id(user_id) -> str:
    if user_id is None:
        return "unknown"
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:12]


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    if not text:
        return 0

    try:
        tiktoken = importlib.import_module("tiktoken")
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: rough estimation if tiktoken is not installed
        # Approximate 4 characters per token for English text
        logger.warning("tiktoken not installed, using approximate token count")
        return len(text) // 4

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
            "anonymized_user_id": _anonymize_user_id(user_id),
            "has_user": user_id is not None,
            "endpoint": endpoint,
            "error": str(e),
        })
        raise
import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from core.config import settings
from utils.logger import get_logger

logger = get_logger("backend.utils.cache")

_redis_client: Optional[Redis] = None
_redis_lock = asyncio.Lock()


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _build_cache_key(
    user_id: int,
    conversation_id: int,
    message: str,
    system_prompt: Optional[str],
    document_ids: Optional[List[int]],
) -> str:
    payload = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "message": _normalize_text(message),
        "system_prompt": _normalize_text(system_prompt or ""),
        "document_ids": sorted(document_ids) if document_ids else None,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{settings.CACHE_PREFIX}:{digest}"


async def _get_redis() -> Optional[Redis]:
    global _redis_client
    if not settings.REDIS_URL:
        return None
    if _redis_client is None:
        async with _redis_lock:
            if _redis_client is None:  # Double-check after acquiring lock
                _redis_client = Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=2,
                )
    return _redis_client


async def get_cached_response(
    user_id: int,
    conversation_id: int,
    message: str,
    system_prompt: Optional[str],
    document_ids: Optional[List[int]],
) -> Optional[Dict[str, Any]]:
    if not settings.CACHE_ENABLED:
        return None

    redis_client = await _get_redis()
    if redis_client is None:
        return None

    cache_key = _build_cache_key(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        system_prompt=system_prompt,
        document_ids=document_ids,
    )

    try:
        cached_value = await redis_client.get(cache_key)
    except Exception as exc:
        logger.warning("Cache read failed", extra={"error": str(exc)})
        return None

    if not cached_value:
        return None

    try:
        return json.loads(cached_value)
    except json.JSONDecodeError:
        return None


async def set_cached_response(
    user_id: int,
    conversation_id: int,
    message: str,
    system_prompt: Optional[str],
    document_ids: Optional[List[int]],
    response: Dict[str, Any],
) -> None:
    if not settings.CACHE_ENABLED:
        return

    redis_client = await _get_redis()
    if redis_client is None:
        return

    cache_key = _build_cache_key(
        user_id=user_id,
        conversation_id=conversation_id,
        message=message,
        system_prompt=system_prompt,
        document_ids=document_ids,
    )

    try:
        payload = json.dumps(response)
        await redis_client.setex(cache_key, settings.CACHE_TTL_SECONDS, payload)
    except Exception as exc:
        logger.warning("Cache write failed", extra={"error": str(exc)})

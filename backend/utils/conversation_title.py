import hashlib
import re
from typing import Optional

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
_LONG_NUMBER_RE = re.compile(r"\b\d{5,}\b")
_SECRET_RE = re.compile(r"\b(password|passcode|pin|token|secret)\b[:\s-]*\S*", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_conversation_title_text(text: Optional[str], max_length: int = 40) -> str:
    if not text:
        return "Conversation"

    sanitized = _URL_RE.sub("[link]", text)
    sanitized = _EMAIL_RE.sub("[email]", sanitized)
    sanitized = _PHONE_RE.sub("[phone]", sanitized)
    sanitized = _LONG_NUMBER_RE.sub("[number]", sanitized)
    sanitized = _SECRET_RE.sub("[secret]", sanitized)
    sanitized = _WHITESPACE_RE.sub(" ", sanitized).strip(" -:\n\t")

    if not sanitized:
        return "Conversation"

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip() + "..."

    return sanitized



def derive_conversation_title(user_message: Optional[str], assistant_response: Optional[str]) -> str:
    preferred_source = assistant_response or user_message
    return sanitize_conversation_title_text(preferred_source)



def title_hash_for_logs(title: Optional[str]) -> Optional[str]:
    if not title:
        return None
    return hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]

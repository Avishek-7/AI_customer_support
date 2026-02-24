from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import List
from collections import OrderedDict
import os
import time


class InMemoryChatHistory(BaseChatMessageHistory):
    """Simple in-memory chat message history."""
    
    def __init__(self):
        self.messages: List[BaseMessage] = []
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the store."""
        self.messages.append(message)
    
    def add_user_message(self, message: str) -> None:
        """Convenience method for adding a human message."""
        self.add_message(HumanMessage(content=message))
    
    def add_ai_message(self, message: str) -> None:
        """Convenience method for adding an AI message."""
        self.add_message(AIMessage(content=message))
    
    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []


# You can replace this with Redis later for scaling
MAX_MEMORY_SESSIONS = int(os.getenv("MEMORY_MAX_SESSIONS", "1000"))
MEMORY_SESSION_TTL_SECONDS = int(os.getenv("MEMORY_SESSION_TTL_SECONDS", "86400"))
memory_store: "OrderedDict[str, tuple[InMemoryChatHistory, float]]" = OrderedDict()


def _evict_oldest_if_needed() -> None:
    now = time.time()

    expired = [
        session_id
        for session_id, (_, updated_at) in memory_store.items()
        if now - updated_at > MEMORY_SESSION_TTL_SECONDS
    ]
    for session_id in expired:
        memory_store.pop(session_id, None)

    while len(memory_store) > MAX_MEMORY_SESSIONS:
        memory_store.popitem(last=False)

def get_memory(session_id: str) -> InMemoryChatHistory:
    """Returns a chat history object for the given user/session.
    
    Creates one if it doesn't exist.
    """
    now = time.time()
    existing = memory_store.get(session_id)
    if existing is not None:
        history, _ = existing
        memory_store[session_id] = (history, now)
        memory_store.move_to_end(session_id)
        return history

    history = InMemoryChatHistory()
    memory_store[session_id] = (history, now)
    memory_store.move_to_end(session_id)
    _evict_oldest_if_needed()
    return history


def clear_session(session_id: str) -> None:
    memory_store.pop(session_id, None)


def save_turn(session_id: str, user_message: str | None = None, ai_message: str | None = None) -> None:
    """Append a conversational turn to memory for a session.

    - Stores messages for later retrieval.
    - Optional helper to persist turns outside chains.
    """
    mem = get_memory(session_id)
    if user_message is not None:
        mem.add_user_message(user_message)
    if ai_message is not None:
        mem.add_ai_message(ai_message)
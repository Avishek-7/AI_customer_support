from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import List


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
memory_store = {}

def get_memory(session_id: str) -> InMemoryChatHistory:
    """Returns a chat history object for the given user/session.
    
    Creates one if it doesn't exist.
    """
    if session_id not in memory_store:
        memory_store[session_id] = InMemoryChatHistory()
    return memory_store[session_id]


def save_turn(session_id: str, user_message: str | None = None, ai_message: str | None = None) -> None:
    """Append a conversational turn to memory for a session.

    - Stores messages for later retrieval.
    - Optional helper to persist turns outside chains.
    """
    mem = get_memory(session_id)
    if user_message:
        mem.add_user_message(user_message)
    if ai_message:
        mem.add_ai_message(ai_message)
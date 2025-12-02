try:
    # Preferred (LangChain >= 0.1.x)
    from langchain.memory import ConversationBufferMemory  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    try:
        # Some versions expose memory classes via community package
        from langchain_community.memory import ConversationBufferMemory  # type: ignore[import-not-found]
    except Exception:
        # Fallback to legacy module path
        from langchain.memory.buffer import ConversationBufferMemory  # type: ignore[import-not-found]

# You can replace this with Redis later for scaling
memory_store = {}

def get_memory(session_id: str) -> ConversationBufferMemory:
    """
    Returns a memory object for the given user/session.
    Creates one if it doesn't exist.
    """

    if session_id not in memory_store:
        memory_store[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
        )
    return memory_store[session_id]


def save_turn(session_id: str, user_message: str | None = None, ai_message: str | None = None) -> None:
    """Append a conversational turn to memory for a session.

    - Stores messages so `load_memory_variables({})["chat_history"]` returns them.
    - Optional helper if you want to persist turns outside chains.
    """
    mem = get_memory(session_id)
    if user_message:
        mem.chat_memory.add_user_message(user_message)
    if ai_message:
        mem.chat_memory.add_ai_message(ai_message)
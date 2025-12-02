from langchain_core.prompts import PromptTemplate

RAG_TEMPLATE = """
{system_prompt}

You are assisting with customer support using provided documents.
Use ONLY the context and conversation history below to answer.
If the answer is NOT in the context, reply exactly:
"I'm sorry, but the requested information is not available in the provided documents."

Conversation history (most recent last):
{chat_history}

Context:
{context}

Question:
{question}

Answer:
"""

rag_prompt = PromptTemplate.from_template(RAG_TEMPLATE)

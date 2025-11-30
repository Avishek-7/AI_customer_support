from langchain_core.prompts import PromptTemplate

RAG_TEMPLATE = """
{system_prompt}

Use ONLY the context below to answer the question.
If the answer is NOT in the context, reply:
"I'm sorry, but the requested information is not available in the provided documents."

Context:
{context}

Question:
{question}

Answer:
"""

rag_prompt = PromptTemplate.from_template(RAG_TEMPLATE)

import google.generativeai as genai
from typing import List
from utils.config import settings

genai.configure(api_key=settings.GOOGLE_API_KEY)

def build_prompt(
        question: str,
        context_chunks: List[str],
        system_prompt: str = "You are an AI customer support assistant."
) -> str:
    """
    Construct the RAG prompt with:
    - usre-defined system instructions
    - reterieved context chunks
    - user's questions 
    """
    context_text = "\n\n".join(context_chunks)

    prompt = f"""
{system_prompt}

You must use ONLY the context below to answer the question.
If the answer is NOT in the context, reply with:
"I'm sorry, but the requested information is not available in the provided dcouments." 

Context:
{context_text}

Question:
{question}

Answer:
""".strip()
    
    return prompt

def generate_answer(
        question: str,
        context_chunks: List[str],
        system_prompt: str = "You are an AI coustomer support assistan."
) -> str:
    """
    Generate an answer using Google Gemini.
    Uses the constructed RAG prompt.
    """

    prompt = build_prompt(question, context_chunks, system_prompt)

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        return response.text
    except Exception as e:
        return f"[ERROR calling Gemini API] {e}"
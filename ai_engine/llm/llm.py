from typing import List
from llm.prompt_template import rag_prompt
from utils.config import settings

from langchain_google_genai import ChatGoogleGenerativeAI


llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.1,
    max_output_tokens=512,
)

def generate_answer(
        question: str,
        context_chunks: List[str],
        system_prompt: str = "You are an AI customer support assistant."
) -> str:
    """
    Generate answer using LangChain + Gemini with proper prompt formatting
    """

    context = "\n\n".join(context_chunks)

    # Format prompt using PromptTemplate
    formatted_prompt = rag_prompt.format(
        system_prompt=system_prompt,
        context=context,
        question=question,
    )

    try:
        result = llm.invoke(formatted_prompt)
        return result.content
    except Exception as e:
        return f"[ERROR calling Gemini API] {e}"
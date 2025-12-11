from typing import List, Optional
from llm.prompt_template import rag_prompt
from utils.config import settings

from langchain_google_genai import ChatGoogleGenerativeAI


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.3,
    max_output_tokens=2048,
)

def generate_answer(
    question: str,
    context_chunks: List[str],
    system_prompt: str = "You are an AI customer support assistant.",
    chat_history: Optional[str] = ""
) -> str:
    """
    Generate answer using LangChain + Gemini with proper prompt formatting
    """

    context = "\n\n".join(context_chunks)

    # Format prompt using PromptTemplate (include chat history)
    formatted_prompt = rag_prompt.format(
        system_prompt=system_prompt,
        context=context,
        question=question,
        chat_history=chat_history or "",
    )

    try:
        result = llm.invoke(formatted_prompt)
        return result.content
    except Exception as e:
        return f"[ERROR calling Gemini API] {e}"
    
async def stream_llm_answer(question, context_chunks, system_prompt, chat_history=""):
    context = "\n\n".join(context_chunks)

    prompt = rag_prompt.format(
        system_prompt=system_prompt,
        context=context,
        question=question,
        chat_history=chat_history or ""
    )

    try:
        async for chunk in llm.astream(prompt):
            content = getattr(chunk, 'content', None)
            if content is not None and content != "":
                yield content
    except Exception as e:
        print(f"[ERROR] Streaming error: {e}")
        yield f"\n\n[Error generating response: {str(e)}]"
from typing import List, Optional
from llm.prompt_template import rag_prompt
from utils.config import settings
from utils.logger import get_logger

from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger("ai_engine.llm")

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
    logger.info("Generating answer", extra={
        "question": question[:100],
        "context_chunks_count": len(context_chunks),
        "has_history": bool(chat_history)
    })

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
        logger.info("Answer generated", extra={"answer_length": len(result.content)})
        return result.content
    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        return f"[ERROR calling Gemini API] {e}"
    
async def stream_llm_answer(question, context_chunks, system_prompt, chat_history=""):
    logger.info("Starting LLM stream", extra={
        "question": question[:100],
        "context_chunks_count": len(context_chunks)
    })
    
    context = "\n\n".join(context_chunks)

    prompt = rag_prompt.format(
        system_prompt=system_prompt,
        context=context,
        question=question,
        chat_history=chat_history or ""
    )

    token_count = 0
    full_response = ""
    
    try:
        async for chunk in llm.astream(prompt):
            content = getattr(chunk, 'content', None)
            if content is not None and content != "":
                token_count += 1
                full_response += content
                
                # Detect repetition loop - if the same phrase appears multiple times, stop
                if len(full_response) > 200:
                    # Check for repeated patterns (looking for 30+ char sequences appearing twice)
                    last_100 = full_response[-100:]
                    earlier = full_response[:-100]
                    if last_100 in earlier:
                        logger.warning("Repetition loop detected, stopping stream")
                        break
                
                yield content
    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield f"\n\n[Error generating response: {str(e)}]"
    finally:
        logger.info("LLM stream completed", extra={"tokens_yielded": token_count})
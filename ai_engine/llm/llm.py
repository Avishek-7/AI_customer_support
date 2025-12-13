from typing import List, Optional
import re
from llm.prompt_template import rag_prompt
from utils.config import settings
from utils.logger import get_logger

from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger("ai_engine.llm")

# Configure LLM with lower temperature to reduce randomness and repetition
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0.2,  # Lower temperature for more focused responses
    max_output_tokens=1536,  # Reduced to prevent over-long responses
    top_p=0.8,  # Nucleus sampling for more focused output
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
    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield f"\n\n[Error generating response: {str(e)}]"
        return
    
    # Post-process to remove duplicate sentences/paragraphs
    deduplicated = _remove_duplicate_sentences(full_response)
    
    if len(deduplicated) < len(full_response):
        removed_chars = len(full_response) - len(deduplicated)
        logger.warning(f"Removed duplicates: {removed_chars} chars ({100*removed_chars/len(full_response):.1f}%)")
    
    logger.info("LLM stream completed", extra={
        "original_length": len(full_response),
        "deduplicated_length": len(deduplicated),
        "token_count": token_count
    })
    
    # Yield deduplicated content as a single token to the pipeline
    # The pipeline will then handle it as a normal token
    yield deduplicated



def _remove_duplicate_sentences(text: str) -> str:
    """Remove duplicate sentences while preserving formatting and allowing legitimate repeats.
    
    Only removes longer sentences/paragraphs that are clearly duplicates.
    Allows short items (like "Register", "Login") to appear in multiple sections.
    """
    
    lines = text.split('\n')
    seen_long_lines = set()  # Only track longer lines (genuine duplicates)
    unique_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Keep empty lines (they provide structure/formatting)
        if not line_stripped:
            unique_lines.append(line)
            continue
        
        # For short lines (< 20 chars), allow them to appear in multiple places
        # These are likely section items like "Register", "Login", etc.
        if len(line_stripped) < 20:
            unique_lines.append(line)
            continue
        
        # For longer lines, check if we've seen them before (true duplicates)
        line_normalized = line_stripped.lower()
        
        if line_normalized in seen_long_lines:
            logger.debug(f"Skipping duplicate paragraph: {line_normalized[:50]}")
            continue
        
        seen_long_lines.add(line_normalized)
        unique_lines.append(line)
    
    # Rejoin with newlines to preserve formatting
    result = '\n'.join(unique_lines)
    return result

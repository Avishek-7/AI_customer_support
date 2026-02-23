from typing import List, Optional
import re
import json
from functools import lru_cache
from llm.prompt_template import rag_prompt
from utils.config import get_settings
from utils.logger import get_logger

from langchain_google_genai import ChatGoogleGenerativeAI

logger = get_logger("ai_engine.llm")


@lru_cache(maxsize=1)
def _get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
        max_output_tokens=1536,
        top_p=0.8,
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
        result = _get_llm().invoke(formatted_prompt)
        logger.info("Answer generated", extra={"answer_length": len(result.content)})
        return result.content
    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        return "[ERROR calling Gemini API]"
    
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

    chunk_count = 0
    full_response = ""
    
    try:
        async for chunk in _get_llm().astream(prompt):
            content = getattr(chunk, 'content', None)
            if content is not None and content != "":
                chunk_count += 1
                full_response += content
                yield content
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
        "chunk_count": chunk_count
    })



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


def critique_answer(
    question: str,
    answer: str,
    context_chunks: List[str],
) -> dict:
    """
    Have the LLM judge/critique its own answer for quality, accuracy, and relevance.
    
    Returns a structured critique with scores and feedback.
    """
    logger.info("Generating self-critique", extra={
        "question": question[:100],
        "answer_length": len(answer),
        "context_chunks_count": len(context_chunks)
    })
    
    context = "\n\n".join(context_chunks)
    
    critique_prompt = f"""You are an AI quality evaluator. Judge the following answer for accuracy, relevance, and quality.

QUESTION:
{question}

CONTEXT PROVIDED:
{context}

ANSWER TO EVALUATE:
{answer}

Provide your critique in the following JSON format:
{{
  "accuracy_score": <0-10>,
  "relevance_score": <0-10>,
  "completeness_score": <0-10>,
  "clarity_score": <0-10>,
  "overall_score": <0-10>,
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "grounded_in_context": <true/false>,
  "summary": "brief summary of the critique"
}}

Evaluate carefully and be honest about strengths and weaknesses."""

    try:
        result = _get_llm().invoke(critique_prompt)
        critique_text = result.content
        
        candidates = []
        fence_matches = re.findall(r"```json\s*(\{.*?\})\s*```", critique_text, re.DOTALL | re.IGNORECASE)
        candidates.extend(fence_matches)
        candidates.extend(re.findall(r'\{.*?\}', critique_text, re.DOTALL))

        for candidate in candidates:
            try:
                critique_data = json.loads(candidate)
                logger.info("Self-critique generated", extra={
                    "overall_score": critique_data.get("overall_score"),
                    "grounded_in_context": critique_data.get("grounded_in_context")
                })
                return critique_data
            except json.JSONDecodeError:
                continue

        return {
            "overall_score": 5,
            "summary": critique_text,
            "error": "Could not parse structured critique"
        }
    except Exception as e:
        logger.error(f"Critique generation error: {e}", exc_info=True)
        return {
            "overall_score": 0,
            "summary": f"Error generating critique: {str(e)}",
            "error": str(e)
        }


def regenerate_answer(
    question: str,
    context_chunks: List[str],
    constraints: str,
    system_prompt: str = "You are an AI customer support assistant.",
    chat_history: Optional[str] = "",
    previous_answer: Optional[str] = None
) -> str:
    """
    Regenerate an answer with specific constraints or modifications.
    
    Args:
        question: The original question
        context_chunks: Retrieved context
        constraints: User-specified constraints (e.g., "make it shorter", "add more detail", "use simpler language")
        system_prompt: System instruction
        chat_history: Conversation history
        previous_answer: The previous answer to improve upon (optional)
    """
    logger.info("Regenerating answer with constraints", extra={
        "question": question[:100],
        "constraints": constraints[:100],
        "has_previous": bool(previous_answer)
    })
    
    context = "\n\n".join(context_chunks)
    
    # Build regeneration prompt
    regeneration_prompt = f"""{system_prompt}

CONTEXT:
{context}

CHAT HISTORY:
{chat_history}

QUESTION:
{question}
"""
    
    if previous_answer:
        regeneration_prompt += f"""
PREVIOUS ANSWER:
{previous_answer}

USER REQUEST:
{constraints}

Please regenerate your answer following the user's request above."""
    else:
        regeneration_prompt += f"""
SPECIAL INSTRUCTIONS:
{constraints}

Please answer the question following the special instructions above."""
    
    try:
        result = _get_llm().invoke(regeneration_prompt)
        logger.info("Answer regenerated", extra={
            "new_answer_length": len(result.content),
            "constraints": constraints[:50]
        })
        return result.content
    except Exception as e:
        logger.error(f"Regeneration error: {e}", exc_info=True)
        return f"[ERROR regenerating answer] {e}"

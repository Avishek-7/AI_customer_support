from typing import List, Dict, Any, Optional
from embeddings.embedder import embed_texts, embed_text
from vectorstore.vector_store import add_embeddings, delete_document
from rag.chunker import chunk_text
from llm.llm import generate_answer
from llm.memory import get_memory
from retriever.retriever import FAISSRetriever

# Index Document into FAISS
def index_document(
        document_id: int,
        title: str,
        content: str,
) -> int:
    """
    1) Chunk the document text
    2) Embed the chunks
    3) Store chunk embeddings + metadata in FAISS
    """

    # Step 1: Chunk the document
    chunks = chunk_text(content)
    if not chunks:
        return 0
    
    # Step 2: Embed chunks
    embeddings = embed_texts(chunks)

    # Step 3: Build metadata for each chunk
    metadatas: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        metadatas.append(
            {
                "document_id": document_id,
                "chunk_id": i,
                "title": title,       
                "text": chunk,
            }
        )

    # Step 4: Add to FAISS
    add_embeddings(embeddings, metadatas)

    return len(chunks)

# Update Document (Delete + Re-index)
def update_document(
        document_id: int,
        title: str,
        content: str,
) -> int:
    """
    Full update workflow:
    - delete old FAISS entries
    - re-chunk the new content
    - re-embed
    - re-index new embeddings
    """

    # Delete all old chunks for this document
    delete_document(document_id)
    
    # Re-chunk
    chunks = chunk_text(content)
    if not chunks: 
        return 0
    
    # Re-embed
    embeddings = embed_texts(chunks)

    # Re-store into FAISS
    metadatas: List[Dict[str, Any]] =[]
    for idx, chunk in enumerate(chunks):
        metadatas.append(
            {
                "document_id": document_id,
                "chunk_id": idx,
                "title": title,
                "text": chunk,
            }
        )
    add_embeddings(embeddings, metadatas)

    return len(chunks)

# Answer Query using RAG (Gemini + FAISS)
def answer_query(
        query: str,
        session_id: str,
        system_prompt: str = "You are an AI customer support assistant.",
        document_ids: Optional[List[int]] = None,
        k: int = 5,
) -> Dict[str, Any]:
    
    # Get memory for session/user
    memory = get_memory(session_id)
    history = memory.load_memory_variables({}).get("chat_history", [])

    # LangChain-compatible Retriever
    retriever = FAISSRetriever(
        k=k,
        allowed_document_ids=document_ids,
    )

    # Retrieve relevant chunks (langchain Documents)
    docs = retriever._get_relevant_documents(query)

    # Prepare context for LLM
    context_chunks = [doc.page_content for doc in docs]

    # Render chat history to text for the LLM prompt
    history_text = "\n".join(
        f"User: {m.content}" if getattr(m, "type", "") == "human" else f"Assistant: {getattr(m, 'content', m)}"
        for m in history
    ) if history else ""

    # Call Gemini LLM with RAG context
    answer = generate_answer(
        question=query,
        context_chunks=context_chunks,
        system_prompt=system_prompt,
        chat_history=history_text,
    )

    # Save conversation to memory
    memory.save_context(
        {"input": query},
        {"output": answer}
    )

    # Extract metdata for frontend UI
    sources = [doc.metadata for doc in docs]
    return {
        "answer": answer,
        "sources": sources,
    }


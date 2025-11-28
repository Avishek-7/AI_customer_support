from typing import List

def chunk_text(
        text: str,
        chunk_size: int = 800,
        chunk_overlap: int = 200
) -> List[str]:
    """
    Simple text splitter.
    - sliding window chunks
    - overlap for context continuity
    - works well for RAG
    """
    text = text.strip().replace("\r\n", "\n")
    chunks = []

    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()

        # move window (with overlap)
        start = end - chunk_overlap
        if start < 0:
            start = 0

    return chunks


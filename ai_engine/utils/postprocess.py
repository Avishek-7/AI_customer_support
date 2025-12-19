import re

def postprocess_answer(text: str) -> str:
    if not text:
        return text
    
    # Normalize whitespace 
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Remove repeated sentences (simple heuristic)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen = set()
    cleaned = []
    for s in sentences:
        key = s.strip().lower()
        if key and key not in seen:
            seen.add(key)
            cleaned.append(s.strip())

    text = " ".join(cleaned)

    # Trim dangling incomplete endings
    text = re.sub(r'([^\.\!\?])$', r'\1', text)

    return text.strip()
import re

def postprocess_answer(text: str) -> str:
    if not text:
        return text
    
    # Normalize whitespace 
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    paragraphs = text.split("\n\n")
    cleaned_paragraphs = []

    for paragraph in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())
        seen = set()
        cleaned = []
        for sentence in sentences:
            key = sentence.strip().lower()
            if key and key not in seen:
                seen.add(key)
                cleaned.append(sentence.strip())

        if cleaned:
            cleaned_paragraphs.append(" ".join(cleaned))

    text = "\n\n".join(cleaned_paragraphs)

    return text.strip()
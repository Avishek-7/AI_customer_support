import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes.
    
    Strips NUL (0x00) characters which PostgreSQL doesn't allow in text fields.
    """
    text = ""
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page in pdf:
        text += page.get_text()

    # Remove NUL characters that can appear in some PDFs
    # PostgreSQL TEXT type doesn't allow NUL bytes
    text = text.replace("\x00", "")
    
    return text.strip()
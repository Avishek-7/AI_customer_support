import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text = ""
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page in pdf:
        text += page.get_text()

    return text.strip()
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

def load_pdf_as_documents(file_path: str) -> List[Document]:
    """
    Load a PDF file into a list of LangChain Document objects.
    Each page becomes a Document with metadata like page number. 
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    loader = PyPDFLoader(str(path))
    documents = loader.load() # List[Document]
    return documents

def extract_text_from_pdf(file_path: str) -> str:
    """
    Load a PDF via LangChain and return plain concatenated text.
    Useful when you just want text to strore in DB or send to AI engine. 
    """
    documents = load_pdf_as_documents(file_path)
    full_text = "\n\n".join(doc.page_content for doc in documents)
    return full_text.strip()

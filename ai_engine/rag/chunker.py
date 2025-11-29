from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def chunk_text(
        text: str,
        chunk_size: int = 800,
        chunk_overlap: int = 200
) -> List[str]:
    """
    Split a long text into overlapping chunks using LangChain's
    RecursiveCharacterTextSplitter. Returns list of strings.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    docs = splitter.create_documents([text])
    chunks = [d.page_content for d in docs]
    return chunks

def chunk_documents(
        documents: List[Document],
        chunk_size: int = 800,
        chunk_overlap: int = 200,
) -> List[Document]:
    """
    Split LangChain Document objects into smaller Documents with preserved metadata. 
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunked_docs = splitter.split_documents(documents)
    return chunked_docs
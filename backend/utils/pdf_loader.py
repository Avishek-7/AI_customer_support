import os
from typing import List, Optional
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

class PDFLoader:
    """Utility class for loading and processing PDF documents."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the PDF loader.
        
        Args:
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    def load_pdf(self, file_path: str) -> str:
        """
        Load text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text from the PDF
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        text = ""
        reader = PdfReader(file_path)
        
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    
    def load_and_split(self, file_path: str) -> List[Document]:
        """
        Load PDF and split into chunks.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document objects with chunked text
        """
        text = self.load_pdf(file_path)
        
        documents = self.text_splitter.create_documents(
            [text],
            metadatas=[{"source": file_path}]
        )
        
        return documents
    
    def load_multiple_pdfs(self, file_paths: List[str]) -> List[Document]:
        """
        Load and process multiple PDF files.
        
        Args:
            file_paths: List of paths to PDF files
            
        Returns:
            List of Document objects from all PDFs
        """
        all_documents = []
        
        for file_path in file_paths:
            try:
                documents = self.load_and_split(file_path)
                all_documents.extend(documents)
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
        
        return all_documents
from sqlalchemy import Column, Integer, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime

class VectorMetadata(Base):
    """Store metadata for FAISS vector embeddings in PostgreSQL for hybrid storage."""
    __tablename__ = "vector_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    faiss_index = Column(Integer, nullable=False)  # Position in FAISS index
    embedding_model = Column(Text, default="all-MiniLM-L6-v2")
    chunk_length = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to document (using string reference for lazy evaluation)
    # This avoids circular import issues
    # document = relationship("Document", back_populates="vector_metadata")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_document_chunk', 'document_id', 'chunk_index'),
    )
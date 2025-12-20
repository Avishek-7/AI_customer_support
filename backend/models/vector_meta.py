from sqlalchemy import Column, Integer, text
from core.database import Base

class VectorMetadata(Base):
    __table__ = "vector_metadata"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer)
    chunk_index = Column(Integer)
    text = Column(text)
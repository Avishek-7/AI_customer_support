from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base

class Document(Base):
    __tablename__ ="documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=True)
    index_status = Column(String, default="pending")
    chunk_count = Column(Integer, default=0)
    
    owner = relationship("User", back_populates="documents")
    chat = relationship("Chat", back_populates="documents")


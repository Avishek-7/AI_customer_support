from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    
    documents = relationship("Document", back_populates="owner")
    chats = relationship("Chat", back_populates="user")
    chat_history = relationship("ChatHistory", back_populates="user")
    

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    response = Column(String)

    user = relationship("User", back_populates="chats")
    documents = relationship("Document", back_populates="owner")
    

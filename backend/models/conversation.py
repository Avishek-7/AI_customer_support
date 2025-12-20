from sqlalchemy import Column, Integer, DateTime, String
from core.database import Base
from datetime import datetime              

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
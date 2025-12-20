from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float
from core.database import Base


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    endpoint = Column(String)
    tokens = Column(Integer)
    latency = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

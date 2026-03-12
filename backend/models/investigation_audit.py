from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from core.database import Base


class InvestigationAudit(Base):
    __tablename__ = "investigation_audit"

    id = Column(Integer, primary_key=True, index=True)
    investigator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    instruction_intent = Column(String(64), nullable=False)
    tools_called = Column(Text, nullable=False, default="[]")
    status = Column(String(32), nullable=False, default="completed")
    latency_ms = Column(Integer, nullable=False, default=0)
    confidence_score = Column(Float, nullable=True)
    hallucination_score = Column(Float, nullable=True)
    alignment_score = Column(Float, nullable=True)
    diagnosis_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

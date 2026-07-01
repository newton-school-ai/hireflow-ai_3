from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from src.config.database import Base

class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    applied = "applied"
    rejected = "rejected"
    interview = "interview"
    offer = "offer"

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    match_score = Column(Float, nullable=True)
    skill_gaps = Column(JSONB, nullable=True)
    resume_path = Column(String, nullable=True)
    status = Column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.pending)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    prep_guide = relationship("PrepGuide", back_populates="application", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application(user_id={self.user_id}, job_id={self.job_id}, status={self.status})>"

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, JSON
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
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    match_score = Column(Float, nullable=True)
    skill_gaps = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    resume_path = Column(String, nullable=True)
    status = Column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.pending)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="applications")
    listing = relationship("Listing", back_populates="applications")
    prep_guide = relationship("PrepGuide", back_populates="application", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application(user_id={self.user_id}, listing_id={self.listing_id}, status={self.status})>"

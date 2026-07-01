from sqlalchemy import Column, Integer, Date, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.config.database import Base

class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    week_start_date = Column(Date, nullable=False)
    metrics = Column(JSONB, nullable=False) # e.g., jobs_applied, interviews_secured, etc.
    content = Column(JSONB, nullable=True) # Could be sections of the report text or summary
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="weekly_reports")

    def __repr__(self):
        return f"<WeeklyReport(user_id={self.user_id}, week_start={self.week_start_date})>"

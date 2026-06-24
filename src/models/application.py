from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.config.database import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    match_score = Column(Float, nullable=True)
    skill_gaps = Column(JSONB, nullable=True)
    resume_path = Column(String, nullable=True)
    status = Column(String, default="planned", nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="applications")
    job = relationship("Job", backref="applications")

    def __repr__(self):
        return f"<Application id={self.id} user_id={self.user_id} job_id={self.job_id} status='{self.status}'>"

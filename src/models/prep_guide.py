from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.config.database import Base

class PrepGuide(Base):
    __tablename__ = "prep_guides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    company_intel = Column(JSONB, nullable=True)
    rounds = Column(JSONB, nullable=True)
    topics = Column(JSONB, nullable=True)
    mock_questions = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="prep_guides")
    job = relationship("Job", backref="prep_guides")

    def __repr__(self):
        return f"<PrepGuide id={self.id} user_id={self.user_id} job_id={self.job_id}>"

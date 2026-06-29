from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text
from sqlalchemy.sql import func
from src.config.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    listing_type = Column(String, nullable=True)
    is_spam = Column(Boolean, default=False)
    spam_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

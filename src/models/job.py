from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime
from sqlalchemy.sql import func
from src.config.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String, nullable=False)
    role_title = Column(String, nullable=False)
    jd_text = Column(Text, nullable=False)
    location = Column(String, nullable=True)
    application_url = Column(String, nullable=True)
    posting_date = Column(String, nullable=True)
    listing_type = Column(String, nullable=True)
    is_spam = Column(Boolean, default=False, nullable=False)
    spam_confidence = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Job id={self.id} company='{self.company_name}' title='{self.role_title}'>"

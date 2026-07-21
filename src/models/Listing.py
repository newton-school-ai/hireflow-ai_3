from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from src.config.database import Base

class ListingType(str, enum.Enum):
    internship = "internship"
    job = "job"

class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    company_name=  Column(String, nullable=False)
    role_title=  Column(String, nullable=False)
    jd_text=  Column(Text, nullable=True)
    location=  Column(String, nullable=True)
    application_url=  Column(String, unique=True, index=True, nullable=False)
    posted_date=  Column(String, nullable=True)
    listing_type=  Column(Enum(ListingType), nullable=False, default=ListingType.job)
    source=  Column(String, nullable=False, default='lever')

    created_at = Column(DateTime(timezone=True), server_default=func.now())
  
    
    # is_spam = Column(Boolean, nullable=False, default=False)
    # spam_confidence = Column(Float, nullable=True)
    

    # Relationships
    applications = relationship("Application", back_populates="listing", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Listing(title={self.role_title}, company={self.company_name})>"

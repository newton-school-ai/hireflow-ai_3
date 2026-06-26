from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.config.database import Base

class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start = Column(Date, nullable=True)
    applied_count = Column(Integer, default=0, nullable=False)
    avg_match_score = Column(Float, nullable=True)
    report_path = Column(String, nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="weekly_reports")

    def __repr__(self):
        return f"<WeeklyReport id={self.id} user_id={self.user_id} week_start={self.week_start}>"

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from src.config.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    mode = Column(String, nullable=True)
    master_profile = Column(JSONB, nullable=True)
    weekly_quota = Column(Integer, default=5, nullable=True)
    confirmation_mode = Column(String, default="batch", nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<User id={self.id} name='{self.name}' email='{self.email}'>"

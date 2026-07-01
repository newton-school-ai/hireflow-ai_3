import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the database URL from the environment, with a default for local development
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/hireflow")

# Create the SQLAlchemy engine
# Note: For asyncpg (if used later), the URL should start with postgresql+asyncpg://
engine = create_engine(DATABASE_URL)

# Create a sessionmaker to spawn new sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for our declarative models
Base = declarative_base()

def get_db():
    """
    Dependency to get a database session for FastAPI endpoints.
    Ensures the session is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

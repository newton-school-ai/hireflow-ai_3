import os
import pytest
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/hireflow")

@pytest.fixture(scope="module")
def engine():
    return create_engine(DATABASE_URL)

def test_tables_exist(engine):
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "users" in tables
    assert "jobs" in tables
    assert "applications" in tables
    assert "prep_guides" in tables
    assert "weekly_reports" in tables

def test_users_table_columns(engine):
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("users")}
    expected_columns = {
        "id", "name", "email", "mode", "master_profile", 
        "weekly_quota", "confirmation_mode", "created_at"
    }
    assert expected_columns.issubset(columns)

def test_jobs_table_columns(engine):
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("jobs")}
    expected_columns = {
        "id", "title", "company", "location", "description", 
        "url", "listing_type", "is_spam", "spam_confidence", "created_at"
    }
    assert expected_columns.issubset(columns)

def test_applications_table_columns(engine):
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("applications")}
    expected_columns = {
        "id", "user_id", "job_id", "match_score", "skill_gaps", 
        "resume_path", "status", "created_at"
    }
    assert expected_columns.issubset(columns)

    # Check foreign keys
    fks = inspector.get_foreign_keys("applications")
    fk_columns = {fk["constrained_columns"][0] for fk in fks}
    assert "user_id" in fk_columns
    assert "job_id" in fk_columns

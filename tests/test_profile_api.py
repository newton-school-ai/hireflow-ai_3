"""
Tests for the Profile API endpoints.
Uses an in-memory SQLite database to avoid requiring PostgreSQL for tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB

from src.config.database import Base, get_db
from src.api.main import app

# ───────── Patch JSONB → JSON for SQLite ─────────
# SQLite doesn't support JSONB; remap it to plain JSON (stored as TEXT).
# This must happen before create_all().

from sqlalchemy import event

@event.listens_for(Base.metadata, "column_reflect")
def _setup_jsonb(inspector, table, column_info):
    if isinstance(column_info.get("type"), JSONB):
        column_info["type"] = JSON()


# Also patch at the model level: replace JSONB columns with JSON
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()


# ───────── Test database setup ─────────

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Yield a test DB session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ───────── Fixtures ─────────


VALID_PROFILE = {
    "name": "Test Student",
    "email": "test@example.com",
    "skills": ["Python", "LangChain", "FastAPI"],
    "mode": "internship",
    "weekly_quota": 5,
    "target_roles": ["AI Engineer Intern"],
    "preferred_locations": ["Bangalore", "Remote"],
    "min_stipend": 15000,
}


# ───────── POST /profile tests ─────────


class TestCreateProfileJSON:
    """Tests for POST /profile with JSON body."""

    def test_create_profile_success(self):
        """POST /profile with valid JSON returns 201 and created user."""
        response = client.post("/profile", json=VALID_PROFILE)
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Profile created successfully"
        assert data["user"]["name"] == "Test Student"
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["mode"] == "internship"
        assert data["user"]["weekly_quota"] == 5
        assert data["user"]["id"] is not None

    def test_create_profile_minimal(self):
        """POST /profile with only required fields uses defaults."""
        response = client.post("/profile", json={
            "name": "Minimal User",
            "email": "minimal@example.com",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["mode"] == "job"
        assert data["user"]["weekly_quota"] == 50
        assert data["user"]["confirmation_mode"] == "batch"

    def test_create_profile_stores_master_profile(self):
        """POST /profile stores skills, target_roles, etc. in master_profile JSON."""
        response = client.post("/profile", json=VALID_PROFILE)
        assert response.status_code == 201
        master = response.json()["user"]["master_profile"]
        assert "Python" in master["skills"]
        assert "AI Engineer Intern" in master["target_roles"]
        assert "Bangalore" in master["preferred_locations"]
        assert master["min_stipend"] == 15000

    def test_create_profile_invalid_mode(self):
        """POST /profile with invalid mode returns 422."""
        payload = {**VALID_PROFILE, "mode": "freelance"}
        response = client.post("/profile", json=payload)
        assert response.status_code == 422

    def test_create_profile_missing_name(self):
        """POST /profile without name returns 422."""
        payload = {"email": "noname@example.com"}
        response = client.post("/profile", json=payload)
        assert response.status_code == 422

    def test_create_profile_invalid_email(self):
        """POST /profile with invalid email returns 422."""
        payload = {**VALID_PROFILE, "email": "not-an-email"}
        response = client.post("/profile", json=payload)
        assert response.status_code == 422

    def test_create_profile_duplicate_email(self):
        """POST /profile with duplicate email returns 409."""
        client.post("/profile", json=VALID_PROFILE)
        response = client.post("/profile", json=VALID_PROFILE)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_confirmation_mode_defaults_to_batch(self):
        """confirmation_mode should default to 'batch' per Issue 4."""
        response = client.post("/profile", json={
            "name": "Batch Default",
            "email": "batch@example.com",
        })
        assert response.status_code == 201
        assert response.json()["user"]["confirmation_mode"] == "batch"

    def test_confirmation_mode_manual(self):
        """confirmation_mode can be set to 'manual'."""
        payload = {**VALID_PROFILE, "confirmation_mode": "manual"}
        response = client.post("/profile", json=payload)
        assert response.status_code == 201
        assert response.json()["user"]["confirmation_mode"] == "manual"


# ───────── GET /profile/{user_id} tests ─────────


class TestGetProfile:
    """Tests for GET /profile/{user_id}."""

    def test_get_profile_success(self):
        """GET /profile/{id} returns the correct profile."""
        create_resp = client.post("/profile", json=VALID_PROFILE)
        user_id = create_resp.json()["user"]["id"]

        response = client.get(f"/profile/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Student"
        assert data["email"] == "test@example.com"
        assert data["id"] == user_id

    def test_get_profile_not_found(self):
        """GET /profile/{nonexistent_id} returns 404."""
        response = client.get("/profile/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# ───────── Root endpoint ─────────


class TestRootEndpoint:
    """Verify the root endpoint still works."""

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "HireFlow API is running"

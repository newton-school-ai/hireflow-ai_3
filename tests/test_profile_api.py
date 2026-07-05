import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.main import app
from src.config.database import Base, get_db
from src.config.settings import settings
from src.models.user import User, UserMode, ConfirmationMode

# Setup test DB using PostgreSQL (same connection as development settings)
engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def cleanup_users():
    # Clean up test users before and after test execution to prevent collisions
    db = TestingSessionLocal()
    db.query(User).filter(User.email.in_([
        "john@example.com", 
        "jane@example.com", 
        "extracted@example.com"
    ])).delete(synchronize_session=False)
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(User).filter(User.email.in_([
        "john@example.com", 
        "jane@example.com", 
        "extracted@example.com"
    ])).delete(synchronize_session=False)
    db.commit()
    db.close()

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_create_profile_json_valid():
    response = client.post(
        "/profile",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "mode": "job",
            "weekly_quota": 10,
            "skills": ["Python", "SQL"],
            "target_roles": ["Backend Developer"]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"
    assert data["mode"] == "job"
    assert data["weekly_quota"] == 10
    assert data["confirmation_mode"] == "batch"
    assert data["master_profile"]["skills"] == ["Python", "SQL"]

def test_create_profile_json_invalid_mode():
    response = client.post(
        "/profile",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "mode": "invalid_mode"
        }
    )
    assert response.status_code == 400
    assert "Invalid mode" in response.json()["detail"]

def test_get_profile_not_found():
    response = client.get("/profile/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User profile not found"

def test_get_profile_success():
    # Setup user
    db = TestingSessionLocal()
    user = User(
        name="Jane Doe",
        email="jane@example.com",
        mode=UserMode.internship,
        confirmation_mode=ConfirmationMode.batch,
        weekly_quota=20,
        master_profile={"skills": ["React"]}
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()

    response = client.get(f"/profile/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["mode"] == "internship"
    assert data["weekly_quota"] == 20

@patch("src.utils.llm_client.LLMClient.extract_profile")
def test_create_profile_pdf_upload(mock_extract):
    mock_extract.return_value = {
        "name": "Extracted Candidate",
        "email": "extracted@example.com",
        "skills": ["FastAPI", "Docker"],
        "experience": [],
        "education": []
    }
    
    with patch("src.api.routes.profile.PdfReader") as mock_pdf_reader:
        mock_reader_instance = mock_pdf_reader.return_value
        mock_page = mock_reader_instance.pages[0]
        mock_reader_instance.pages = [mock_page]
        mock_page.extract_text.return_value = "Extracted Candidate resume text"
        
        pdf_file = ("resume.pdf", b"%PDF-1.4 dummy content", "application/pdf")
        
        response = client.post(
            "/profile",
            files={"file": pdf_file},
            data={"mode": "internship", "weekly_quota": "15"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Extracted Candidate"
        assert data["email"] == "extracted@example.com"
        assert data["mode"] == "internship"
        assert data["weekly_quota"] == 15
        assert data["confirmation_mode"] == "batch"
        assert data["master_profile"]["skills"] == ["FastAPI", "Docker"]

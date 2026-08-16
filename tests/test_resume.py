import pytest
from unittest.mock import MagicMock, patch

from src.models.user import User
from src.models.job import Job
from src.pipelines.resume_generator import ResumeTailoringEngine


@pytest.fixture
def mock_db_session():
    with patch("src.pipelines.resume_generator.SessionLocal") as mock_session:
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        yield session_instance


@pytest.fixture
def mock_llm_client():
    with patch("src.pipelines.resume_generator.get_llm_client") as mock_get_client:
        client_instance = MagicMock()
        mock_get_client.return_value = client_instance
        yield client_instance


def test_resume_formatting_and_summary_tone(mock_db_session, mock_llm_client):
    # Setup mock DB
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.mode = "internship"
    mock_user.master_profile = {
        "skills": ["python", "react"],
        "projects": [{"name": "proj1"}, {"name": "proj2"}],
        "experience": [],
        "education": []
    }
    
    mock_job = MagicMock(spec=Job)
    mock_job.id = 101
    mock_job.title = "Frontend Intern"
    mock_job.description = "Looking for React skills."

    # Configure query chain to return our mocks
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_user, mock_job]
    
    # Configure mock LLM extract output
    mock_llm_client.extract.return_value = {
        "summary": "Enthusiastic intern ready to learn.",
        "skills": ["react", "python"],
        "projects": [{"name": "proj1"}],
        "experience": [],
        "education": []
    }

    engine = ResumeTailoringEngine()
    result = engine.tailor(user_id=1, job_id=101)

    assert "summary" in result
    assert result["skills"] == ["react", "python"]
    # Check that mode_instruction was passed in prompt
    called_prompt = mock_llm_client.extract.call_args[0][0]
    assert "internship" in called_prompt.lower()
    assert "enthusiasm" in called_prompt.lower()


def test_hallucination_checker(mock_db_session, mock_llm_client):
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.master_profile = {
        "skills": ["python"],
        "projects": [{"name": "Auth API"}]
    }
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user

    engine = ResumeTailoringEngine()
    
    # Valid result
    valid_result = {
        "skills": ["python"],
        "projects": [{"name": "Auth API"}]
    }
    hallucinations = engine.check_hallucination(valid_result, user_id=1)
    assert len(hallucinations) == 0

    # Invalid result (hallucinated skills and projects)
    invalid_result = {
        "skills": ["python", "docker"],
        "projects": [{"name": "Auth API"}, {"name": "Fake Project"}]
    }
    hallucinations = engine.check_hallucination(invalid_result, user_id=1)
    assert len(hallucinations) == 2
    assert "Skill: docker" in hallucinations
    assert "Project: Fake Project" in hallucinations


def test_different_jds_produce_different_outputs(mock_db_session, mock_llm_client):
    """
    Test that tailoring with two different JDs passes different job descriptions to the LLM.
    """
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.mode = "job"
    mock_user.master_profile = {"skills": ["python", "go"]}
    
    mock_job1 = MagicMock(spec=Job)
    mock_job1.id = 101
    mock_job1.title = "Python Dev"
    mock_job1.description = "Need python"

    mock_job2 = MagicMock(spec=Job)
    mock_job2.id = 102
    mock_job2.title = "Go Dev"
    mock_job2.description = "Need go"

    # We mock the sequence of .first() calls
    # Call 1 (tailor job1): returns user, then job1
    # Call 2 (tailor job2): returns user, then job2
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        mock_user, mock_job1,
        mock_user, mock_job2
    ]

    mock_llm_client.extract.return_value = {}

    engine = ResumeTailoringEngine()
    
    engine.tailor(user_id=1, job_id=101)
    prompt1 = mock_llm_client.extract.call_args[0][0]
    assert "Python Dev" in prompt1
    
    engine.tailor(user_id=1, job_id=102)
    prompt2 = mock_llm_client.extract.call_args[0][0]
    assert "Go Dev" in prompt2

    assert prompt1 != prompt2

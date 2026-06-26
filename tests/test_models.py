import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config.database import Base, DATABASE_URL
from src.models.user import User
from src.models.job import Job
from src.models.application import Application
from src.models.prep_guide import PrepGuide
from src.models.report import WeeklyReport

@pytest.fixture(scope="module")
def db_session():
    # Use the configured database
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    yield session
    
    # Clean up database records
    session.query(WeeklyReport).delete()
    session.query(PrepGuide).delete()
    session.query(Application).delete()
    session.query(Job).delete()
    session.query(User).delete()
    session.commit()
    session.close()

def test_user_model(db_session):
    user = User(
        name="John Doe",
        email="john@example.com",
        mode="job",
        master_profile={"skills": ["Python", "SQL"]},
        weekly_quota=10,
        confirmation_mode="individual"
    )
    db_session.add(user)
    db_session.commit()
    
    db_user = db_session.query(User).filter_by(email="john@example.com").first()
    assert db_user is not None
    assert db_user.id is not None
    assert db_user.name == "John Doe"
    assert db_user.mode == "job"
    assert db_user.master_profile == {"skills": ["Python", "SQL"]}
    assert db_user.weekly_quota == 10
    assert db_user.confirmation_mode == "individual"
    assert isinstance(db_user.created_at, datetime)

def test_job_model(db_session):
    job = Job(
        company_name="Google",
        role_title="Software Engineer",
        jd_text="Looking for a Python dev...",
        location="Remote",
        application_url="https://google.com/jobs",
        posting_date="2026-06-25",
        listing_type="job",
        is_spam=False,
        spam_confidence=0.01
    )
    db_session.add(job)
    db_session.commit()
    
    db_job = db_session.query(Job).filter_by(company_name="Google").first()
    assert db_job is not None
    assert db_job.id is not None
    assert db_job.role_title == "Software Engineer"
    assert db_job.jd_text == "Looking for a Python dev..."
    assert db_job.location == "Remote"
    assert db_job.application_url == "https://google.com/jobs"
    assert db_job.posting_date == "2026-06-25"
    assert db_job.listing_type == "job"
    assert db_job.is_spam is False
    assert db_job.spam_confidence == 0.01

def test_application_model(db_session):
    # Retrieve user and job created in previous tests
    user = db_session.query(User).filter_by(email="john@example.com").first()
    job = db_session.query(Job).filter_by(company_name="Google").first()
    
    app = Application(
        user_id=user.id,
        job_id=job.id,
        match_score=0.85,
        skill_gaps=["C++"],
        resume_path="/data/resumes/john_doe.pdf",
        status="planned"
    )
    db_session.add(app)
    db_session.commit()
    
    db_app = db_session.query(Application).filter_by(user_id=user.id, job_id=job.id).first()
    assert db_app is not None
    assert db_app.id is not None
    assert db_app.match_score == 0.85
    assert db_app.skill_gaps == ["C++"]
    assert db_app.resume_path == "/data/resumes/john_doe.pdf"
    assert db_app.status == "planned"
    
    # Check relationships
    assert db_app.user.id == user.id
    assert db_app.job.id == job.id
    assert app in user.applications
    assert app in job.applications

def test_prep_guide_model(db_session):
    user = db_session.query(User).filter_by(email="john@example.com").first()
    job = db_session.query(Job).filter_by(company_name="Google").first()
    
    guide = PrepGuide(
        user_id=user.id,
        job_id=job.id,
        company_intel={"culture": "Good"},
        rounds=[{"round": 1, "type": "technical"}],
        topics={"weak": ["Docker"]},
        mock_questions=[{"q": "What is Docker?"}]
    )
    db_session.add(guide)
    db_session.commit()
    
    db_guide = db_session.query(PrepGuide).filter_by(user_id=user.id, job_id=job.id).first()
    assert db_guide is not None
    assert db_guide.id is not None
    assert db_guide.company_intel == {"culture": "Good"}
    assert db_guide.rounds == [{"round": 1, "type": "technical"}]
    assert db_guide.topics == {"weak": ["Docker"]}
    assert db_guide.mock_questions == [{"q": "What is Docker?"}]
    
    assert db_guide.user.id == user.id
    assert db_guide.job.id == job.id

def test_weekly_report_model(db_session):
    user = db_session.query(User).filter_by(email="john@example.com").first()
    
    report = WeeklyReport(
        user_id=user.id,
        week_start=date(2026, 6, 22),
        applied_count=5,
        avg_match_score=0.82,
        report_path="/reports/week_25.html",
        email_sent_at=datetime(2026, 6, 25, 10, 0, 0)
    )
    db_session.add(report)
    db_session.commit()
    
    db_report = db_session.query(WeeklyReport).filter_by(user_id=user.id).first()
    assert db_report is not None
    assert db_report.id is not None
    assert db_report.week_start == date(2026, 6, 22)
    assert db_report.applied_count == 5
    assert db_report.avg_match_score == 0.82
    assert db_report.report_path == "/reports/week_25.html"
    assert db_report.email_sent_at.replace(tzinfo=None) == datetime(2026, 6, 25, 10, 0, 0)
    
    assert db_report.user.id == user.id

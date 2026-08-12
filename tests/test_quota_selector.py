import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone

from src.models.application import Application, ApplicationStatus
from src.models.job import Job
from src.models.user import User, ConfirmationMode
from src.pipelines.quota_selector import QuotaSelector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_db():
    return MagicMock()

def _make_user(quota=3, blacklist=["badco"]):
    user = MagicMock(spec=User)
    user.id = 1
    user.weekly_quota = quota
    user.master_profile = {"blacklist_companies": blacklist}
    user.confirmation_mode = ConfirmationMode.batch
    return user

def _make_job(job_id, company, days_old=5):
    job = MagicMock(spec=Job)
    job.id = job_id
    job.title = f"Role {job_id}"
    job.company = company
    job.posted_date = datetime.now(timezone.utc) - timedelta(days=days_old)
    return job

def _make_app(app_id, job, match_score, status=ApplicationStatus.pending):
    app = MagicMock(spec=Application)
    app.id = app_id
    app.user_id = 1
    app.job_id = job.id
    app.job = job
    app.match_score = match_score
    app.status = status
    app.skill_gaps = {}
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateWeeklyPlan:
    def test_selects_top_n_jobs(self):
        db = _make_mock_db()
        user = _make_user(quota=2)
        
        # 3 pending apps, user quota is 2
        j1 = _make_job(1, "GoodCo")
        a1 = _make_app(1, j1, 0.9)
        j2 = _make_job(2, "OtherCo")
        a2 = _make_app(2, j2, 0.8)
        j3 = _make_job(3, "ThirdCo")
        a3 = _make_app(3, j3, 0.7)
        
        def db_query_side_effect(model):
            if model == Application:
                mock_app_query = MagicMock()
                mock_app_query.filter.return_value.all.return_value = []
                mock_app_query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [a1, a2, a3]
                return mock_app_query
            elif model == User:
                mock_user_query = MagicMock()
                mock_user_query.filter.return_value.first.return_value = user
                return mock_user_query
                
        db.query.side_effect = db_query_side_effect
        
        selector = QuotaSelector(db)
        plan = selector.generate_weekly_plan(1)
        
        assert len(plan["plan"]) == 2
        assert plan["plan"][0]["job_id"] == 1
        assert plan["plan"][1]["job_id"] == 2
        assert a1.status == ApplicationStatus.planned
        assert a2.status == ApplicationStatus.planned
        assert a3.status == ApplicationStatus.pending # unchanged

    def test_filters_blacklist_and_expired(self):
        db = _make_mock_db()
        user = _make_user(quota=2, blacklist=["badco"])
        
        j1 = _make_job(1, "GoodCo")
        a1 = _make_app(1, j1, 0.9)
        j2 = _make_job(2, "BadCo") # Blacklisted
        a2 = _make_app(2, j2, 0.8)
        j3 = _make_job(3, "OldCo", days_old=40) # Expired
        a3 = _make_app(3, j3, 0.7)
        j4 = _make_job(4, "NewCo")
        a4 = _make_app(4, j4, 0.6)
        
        db.query.return_value.filter.return_value.first.return_value = user
        db.query.return_value.filter.return_value.all.side_effect = [[], [a1, a2, a3, a4]]
        
        # Query chain mocking for pending apps
        # db.query().join().filter().order_by().all() -> returns [a1, a2, a3, a4]
        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [a1, a2, a3, a4]
        
        # We need to correctly route the two `all()` calls in the function
        # 1: existing_planned query
        # 2: pending_apps query
        def db_query_side_effect(model):
            if model == Application:
                mock_app_query = MagicMock()
                # for existing planned: filter().all()
                # for pending: join().filter().order_by().all()
                mock_app_query.filter.return_value.all.return_value = []
                mock_app_query.join.return_value.filter.return_value.order_by.return_value.all.return_value = [a1, a2, a3, a4]
                return mock_app_query
            elif model == User:
                mock_user_query = MagicMock()
                mock_user_query.filter.return_value.first.return_value = user
                return mock_user_query
                
        db.query.side_effect = db_query_side_effect
        
        selector = QuotaSelector(db)
        plan = selector.generate_weekly_plan(1)
        
        assert len(plan["plan"]) == 2
        assert plan["plan"][0]["job_id"] == 1
        assert plan["plan"][1]["job_id"] == 4 # Skips 2 and 3


class TestSwapJob:
    def test_swap_updates_status(self):
        db = _make_mock_db()
        j1 = _make_job(1, "A")
        a1 = _make_app(1, j1, 0.9, ApplicationStatus.planned)
        j2 = _make_job(2, "B")
        a2 = _make_app(2, j2, 0.8, ApplicationStatus.pending)
        
        def filter_side_effect(*args):
            mock_filter = MagicMock()
            # Simplistic mock for the first() calls
            if "remove_job_id" in str(args) or a1.job_id in [1]: 
                # This is a hacky mock for the specific test, we'll just return a1 on first call and a2 on second
                pass
            return mock_filter
            
        # Proper mocking of the query sequence
        mock_q1 = MagicMock()
        mock_q1.first.return_value = a1
        mock_q2 = MagicMock()
        mock_q2.first.return_value = a2
        
        # The swap_job function makes two .filter().first() calls, then calls generate_weekly_plan
        # We'll mock the filter calls directly
        
        db.query.return_value.filter.side_effect = [mock_q1, mock_q2]
        
        # Mock generate_weekly_plan to just return something
        selector = QuotaSelector(db)
        selector.generate_weekly_plan = MagicMock(return_value={"plan": []})
        
        selector.swap_job(1, 1, 2)
        
        assert a1.status == ApplicationStatus.pending
        assert a2.status == ApplicationStatus.planned
        db.commit.assert_called_once()

class TestConfirmPlan:
    def test_confirm_updates_status(self):
        db = _make_mock_db()
        j1 = _make_job(1, "A")
        a1 = _make_app(1, j1, 0.9, ApplicationStatus.planned)
        
        mock_query = MagicMock()
        mock_query.all.return_value = [a1]
        db.query.return_value.filter.return_value = mock_query
        
        selector = QuotaSelector(db)
        result = selector.confirm_plan(1, [1])
        
        assert a1.status == ApplicationStatus.confirmed
        assert result["status"] == "success"
        db.commit.assert_called_once()

    def test_confirm_fails_if_not_planned(self):
        db = _make_mock_db()
        
        mock_query = MagicMock()
        mock_query.all.return_value = [] # Missing the requested job
        db.query.return_value.filter.return_value = mock_query
        
        selector = QuotaSelector(db)
        with pytest.raises(ValueError, match="Some jobs are not currently planned"):
            selector.confirm_plan(1, [1])

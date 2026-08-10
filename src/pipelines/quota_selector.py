"""
Weekly Quota Selector and Confirmation Flow

Selects the top N jobs from the ranked list, filters out blacklisted or 
expired jobs, and waits for user confirmation before advancing the state
to resume generation.
"""

from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.models.application import Application, ApplicationStatus
from src.models.job import Job
from src.models.user import User

logger = logging.getLogger(__name__)


class QuotaSelector:
    def __init__(self, db: Session):
        self.db = db

    def generate_weekly_plan(self, user_id: int) -> dict:
        """
        Generates or retrieves the weekly plan for the user.
        Selects top N (weekly_quota) jobs from pending applications.
        Filters out:
          - already applied (status != pending and != planned)
          - expired (posted > 30 days ago)
          - user blacklist
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Check if a planned plan already exists
        existing_planned = (
            self.db.query(Application)
            .filter(
                Application.user_id == user_id,
                Application.status == ApplicationStatus.planned
            )
            .all()
        )

        quota = user.weekly_quota
        profile = user.master_profile or {}
        blacklist = [c.lower() for c in profile.get("blacklist_companies", [])]
        
        # Thirty days ago
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

        planned_apps = list(existing_planned)
        
        # If we need more to fill the quota, fetch pending applications
        if len(planned_apps) < quota:
            needed = quota - len(planned_apps)
            
            pending_apps = (
                self.db.query(Application)
                .join(Job)
                .filter(
                    Application.user_id == user_id,
                    Application.status == ApplicationStatus.pending
                )
                .order_by(desc(Application.match_score))
                .all()
            )
            
            # Filter and select
            selected = []
            for app in pending_apps:
                job = app.job
                # Filter expired
                if job.posted_date and job.posted_date < cutoff_date:
                    continue
                # Filter blacklist
                if job.company and job.company.lower() in blacklist:
                    continue
                
                selected.append(app)
                if len(selected) >= needed:
                    break
            
            # Mark selected as planned
            for app in selected:
                app.status = ApplicationStatus.planned
                planned_apps.append(app)
                
            if selected:
                self.db.commit()
                logger.info(f"Added {len(selected)} jobs to weekly plan for user {user_id}")

        # Format output
        plan_details = []
        for app in planned_apps:
            # Re-sort by match_score just in case
            job = app.job
            plan_details.append({
                "application_id": app.id,
                "job_id": job.id,
                "role_title": job.title,
                "company_name": job.company,
                "match_score": app.match_score,
                "skill_gaps": app.skill_gaps,
                "resume_summary": "Tailored resume will be generated upon confirmation."
            })
            
        plan_details.sort(key=lambda x: x["match_score"] or 0, reverse=True)

        return {
            "user_id": user_id,
            "quota": quota,
            "confirmation_mode": user.confirmation_mode.value,
            "plan": plan_details
        }

    def swap_job(self, user_id: int, remove_job_id: int, add_job_id: int) -> dict:
        """
        Swaps a job in the weekly plan with another job.
        remove_job_id is set to pending, add_job_id is set to planned.
        """
        app_to_remove = self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.job_id == remove_job_id,
            Application.status == ApplicationStatus.planned
        ).first()
        
        if not app_to_remove:
            raise ValueError(f"Job {remove_job_id} is not currently planned for user {user_id}")

        app_to_add = self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.job_id == add_job_id,
            Application.status == ApplicationStatus.pending
        ).first()
        
        if not app_to_add:
            raise ValueError(f"Job {add_job_id} is not a valid pending job for user {user_id}")

        app_to_remove.status = ApplicationStatus.pending
        app_to_add.status = ApplicationStatus.planned
        self.db.commit()
        
        logger.info(f"Swapped job {remove_job_id} with {add_job_id} for user {user_id}")
        return self.generate_weekly_plan(user_id)

    def confirm_plan(self, user_id: int, confirmed_job_ids: list[int]) -> dict:
        """
        Confirms the plan for the specified jobs, triggering the next pipeline phase.
        Sets status from planned to confirmed.
        """
        apps_to_confirm = self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.job_id.in_(confirmed_job_ids),
            Application.status == ApplicationStatus.planned
        ).all()

        if len(apps_to_confirm) != len(confirmed_job_ids):
            found_ids = [app.job_id for app in apps_to_confirm]
            missing = set(confirmed_job_ids) - set(found_ids)
            raise ValueError(f"Some jobs are not currently planned: {missing}")

        for app in apps_to_confirm:
            app.status = ApplicationStatus.confirmed

        self.db.commit()
        logger.info(f"Confirmed {len(apps_to_confirm)} jobs for user {user_id}. Proceeding to resume generation.")

        return {
            "status": "success",
            "message": f"{len(apps_to_confirm)} applications confirmed and queued for resume generation.",
            "confirmed_job_ids": confirmed_job_ids
        }

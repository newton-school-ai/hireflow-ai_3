import argparse
import json
import logging
from typing import Any

from src.config.database import SessionLocal
from src.models.user import User
from src.models.job import Job
from src.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)

class ResumeTailoringEngine:
    def __init__(self):
        self.llm_client = get_llm_client()

    def tailor(self, user_id: int, job_id: int) -> dict[str, Any]:
        """
        Takes a user ID and job ID, fetches them from the DB, and generates
        a tailored resume output using the LLM.
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            profile = user.master_profile or {}
            jd_text = job.description or ""
            job_title = job.title or ""
            user_mode = user.mode.value if hasattr(user.mode, "value") else str(user.mode)

            prompt = self._build_prompt(profile, jd_text, job_title, user_mode)
            
            # Using extract to get JSON output
            result = self.llm_client.extract(prompt)
            
            if not isinstance(result, dict):
                raise RuntimeError("LLM output is not a JSON object")
                
            return result
        finally:
            db.close()

    def _build_prompt(self, profile: dict, jd_text: str, job_title: str, user_mode: str) -> str:
        profile_json = json.dumps(profile, indent=2)
        
        mode_instruction = ""
        if str(user_mode).lower() == "internship":
            mode_instruction = "Ensure the summary highlights enthusiasm, willingness to learn, and foundational skills suitable for an internship."
        else:
            mode_instruction = "Ensure the summary highlights professional impact, leadership, and proven expertise suitable for a full-time role."

        prompt = f"""
You are an expert Resume Writer and ATS Optimizer. Your task is to generate a highly tailored resume for the user based on their profile and the provided job description.

CRITICAL RULE: DO NOT HALLUCINATE OR INVENT ANYTHING. 
You must ONLY use the skills, experiences, and projects that are present in the provided user profile. Do not add any new skills, do not claim experience with technologies they don't have, and do not make up projects or employment history.

Job Title: {job_title}
Job Description: {jd_text}

User Profile:
{profile_json}

Instructions:
1. summary: Generate a 2-4 sentence professional summary tailored to the job description. {mode_instruction}
2. projects: Select exactly 2 to 3 projects from the user's profile that are MOST relevant to the job description. Copy their details exactly as provided.
3. skills: Reorder the user's skills so that the skills mentioned or prioritized in the job description appear first. ONLY use skills present in the user profile. Do not add new ones.
4. experience: Include the user's experience exactly as provided.
5. education: Include the user's education exactly as provided.

Return a valid JSON object with the following keys:
- "summary" (string)
- "skills" (array of strings)
- "projects" (array of objects)
- "experience" (array of objects)
- "education" (array of objects)
"""
        return prompt.strip()

    def check_hallucination(self, result: dict, user_id: int) -> list[str]:
        """
        Checks if the LLM output hallucinated any skills or projects not present in the user profile.
        Returns a list of hallucinated items (empty if none).
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            profile = user.master_profile or {}
        finally:
            db.close()
            
        user_skills = {s.lower().strip() for s in profile.get("skills", [])}
        user_project_names = {p.get("name", "").lower().strip() for p in profile.get("projects", [])}
        
        hallucinated = []
        
        for skill in result.get("skills", []):
            if skill.lower().strip() not in user_skills:
                hallucinated.append(f"Skill: {skill}")
                
        for proj in result.get("projects", []):
            proj_name = proj.get("name", "").lower().strip()
            if proj_name not in user_project_names:
                hallucinated.append(f"Project: {proj.get('name')}")
                
        return hallucinated

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HireFlow Resume Tailoring Engine")
    parser.add_argument("--user-id", type=int, required=True, help="User ID")
    parser.add_argument("--compare-jobs", type=int, nargs=2, help="Two Job IDs to compare generated resumes")
    args = parser.parse_args()

    engine = ResumeTailoringEngine()

    if args.compare_jobs:
        job1, job2 = args.compare_jobs
        print(f"--- Generating Resume for Job {job1} ---")
        res1 = engine.tailor(user_id=args.user_id, job_id=job1)
        print("Summary:", res1.get("summary"))
        print("Top 5 Skills:", res1.get("skills", [])[:5])
        print("Selected Projects:", [p.get("name") for p in res1.get("projects", [])])
        
        print(f"\\n--- Generating Resume for Job {job2} ---")
        res2 = engine.tailor(user_id=args.user_id, job_id=job2)
        print("Summary:", res2.get("summary"))
        print("Top 5 Skills:", res2.get("skills", [])[:5])
        print("Selected Projects:", [p.get("name") for p in res2.get("projects", [])])
    else:
        print("Please provide --compare-jobs with 2 job IDs")

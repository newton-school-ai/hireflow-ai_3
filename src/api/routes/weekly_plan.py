from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.pipelines.quota_selector import QuotaSelector

router = APIRouter(prefix="/weekly-plan", tags=["Weekly Plan"])


class SwapRequest(BaseModel):
    remove_job_id: int
    add_job_id: int


class ConfirmRequest(BaseModel):
    confirmed_job_ids: list[int]


@router.get("/{user_id}")
def get_weekly_plan(user_id: int, db: Session = Depends(get_db)):
    """
    Generates or retrieves the weekly plan for the user, selecting top N jobs.
    """
    try:
        selector = QuotaSelector(db)
        plan = selector.generate_weekly_plan(user_id)
        return plan
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/swap")
def swap_job(user_id: int, request: SwapRequest, db: Session = Depends(get_db)):
    """
    Swaps a job in the current weekly plan for another pending job.
    """
    try:
        selector = QuotaSelector(db)
        new_plan = selector.swap_job(user_id, request.remove_job_id, request.add_job_id)
        return new_plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/confirm")
def confirm_plan(user_id: int, request: ConfirmRequest, db: Session = Depends(get_db)):
    """
    Confirms the plan, changing job status to 'confirmed' and advancing to resume generation.
    """
    try:
        selector = QuotaSelector(db)
        result = selector.confirm_plan(user_id, request.confirmed_job_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

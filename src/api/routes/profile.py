"""
Profile API routes.
POST /profile — Create a user profile from JSON or PDF resume upload.
GET /profile/{user_id} — Retrieve a user profile by ID.
"""

import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.schemas import ProfileCreateRequest, ProfileCreatedResponse, ProfileResponse
from src.config.database import get_db
from src.models.user import ConfirmationMode, User, UserMode
from src.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Profile"])


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF file."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        full_text = "\n".join(text_parts)
        if not full_text.strip():
            raise ValueError("PDF contains no extractable text")
        return full_text
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PyPDF2 is not installed. Run: pip install PyPDF2",
        )


def _build_master_profile(data: dict) -> dict:
    """Build the master_profile JSONB payload from incoming data."""
    return {
        "skills": data.get("skills", []),
        "target_roles": data.get("target_roles", []),
        "preferred_locations": data.get("preferred_locations", []),
        "min_stipend": data.get("min_stipend"),
        "experience": data.get("experience", []),
        "education": data.get("education", []),
        "projects": data.get("projects", []),
    }


def _create_user_from_data(db: Session, data: dict) -> User:
    """Create a User row from a flat dict of profile fields."""
    # Resolve mode
    mode_str = data.get("mode", "job")
    try:
        mode = UserMode(mode_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid mode '{mode_str}'. Must be 'internship' or 'job'.",
        )

    # Resolve confirmation_mode
    conf_str = data.get("confirmation_mode", "batch")
    try:
        confirmation_mode = ConfirmationMode(conf_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid confirmation_mode '{conf_str}'. Must be 'manual', 'auto', or 'batch'.",
        )

    user = User(
        name=data["name"],
        email=data["email"],
        mode=mode,
        weekly_quota=data.get("weekly_quota", 50),
        confirmation_mode=confirmation_mode,
        master_profile=_build_master_profile(data),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{data['email']}' already exists.",
        )

    return user


# ────────────────────────── Endpoints ──────────────────────────


@router.post(
    "/profile",
    response_model=ProfileCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user profile from JSON",
    description="Accepts a JSON body with profile fields. Stores the user in the database.",
)
def create_profile_json(
    profile: ProfileCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a user profile from a JSON payload."""
    data = profile.model_dump()
    user = _create_user_from_data(db, data)
    logger.info("Created user %s (id=%d) from JSON", user.email, user.id)
    return ProfileCreatedResponse(
        message="Profile created successfully",
        user=ProfileResponse.model_validate(user),
    )


@router.post(
    "/profile/upload",
    response_model=ProfileCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user profile from a PDF resume",
    description=(
        "Upload a PDF resume. The LLM extracts structured data (name, email, "
        "skills, experience, etc.) and creates the user profile."
    ),
)
async def create_profile_from_resume(
    file: UploadFile = File(..., description="PDF resume file"),
    db: Session = Depends(get_db),
):
    """Upload a PDF resume → LLM extracts structured profile → stores in DB."""
    # Validate file type
    if file.content_type not in ("application/pdf",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted. Received: " + str(file.content_type),
        )

    # Read and extract text
    file_bytes = await file.read()
    resume_text = _extract_text_from_pdf(file_bytes)

    # Call LLM for extraction
    try:
        llm_client = get_llm_client()
        extracted = await llm_client.extract_profile_from_resume(resume_text)
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM extraction failed: {exc}",
        )

    # Validate required fields from LLM output
    if not extracted.get("name") or not extracted.get("email"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "LLM could not extract required fields (name, email) from the resume. "
                "Please upload a clearer resume or create your profile via JSON."
            ),
        )

    # Set defaults for fields the LLM doesn't produce
    extracted.setdefault("mode", "job")
    extracted.setdefault("weekly_quota", 50)
    extracted.setdefault("confirmation_mode", "batch")

    user = _create_user_from_data(db, extracted)
    logger.info("Created user %s (id=%d) from resume upload", user.email, user.id)
    return ProfileCreatedResponse(
        message="Profile created from resume successfully",
        user=ProfileResponse.model_validate(user),
    )


@router.get(
    "/profile/{user_id}",
    response_model=ProfileResponse,
    summary="Get a user profile by ID",
    description="Returns the full user profile for the given user_id.",
)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    """Retrieve a user profile by its ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found.",
        )
    return ProfileResponse.model_validate(user)

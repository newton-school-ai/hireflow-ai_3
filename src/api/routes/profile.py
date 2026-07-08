from io import BytesIO
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pypdf import PdfReader
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from src.config.database import get_db
from src.models.user import ConfirmationMode, User, UserMode
from src.utils.llm_client import BaseLLMClient, LLMClientError, get_llm_client

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str
    skills: list[str] = Field(default_factory=list)
    mode: Literal["internship", "job"]
    weekly_quota: int = Field(default=10, ge=1)
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    min_stipend: int | None = Field(default=None, ge=0)
    confirmation_mode: Literal["batch", "individual"] = "batch"

    model_config = ConfigDict(extra="allow")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("email must be a valid email address")
        return value


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    mode: UserMode
    weekly_quota: int
    confirmation_mode: ConfirmationMode
    master_profile: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    profile = await _profile_from_request(request)
    user = _build_user(profile)

    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A profile with this email already exists.",
        ) from exc

    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return user


async def _profile_from_request(
    request: Request,
) -> ProfileCreate:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        try:
            return ProfileCreate.model_validate(await request.json())
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=exc.errors(),
            ) from exc

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("resume") or form.get("file")
        if not isinstance(upload, (UploadFile, StarletteUploadFile)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload a PDF file using form field 'resume' or 'file'.",
            )
        try:
            llm_client = get_llm_client()
        except LLMClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        return await _profile_from_pdf(upload, llm_client)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Send either application/json or multipart/form-data.",
    )


async def _profile_from_pdf(
    upload: UploadFile,
    llm_client: BaseLLMClient,
) -> ProfileCreate:
    if upload.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume uploads are supported.",
        )

    resume_text = _extract_pdf_text(await upload.read())
    if not resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the uploaded PDF.",
        )

    try:
        extracted = llm_client.extract_profile(resume_text)
        return ProfileCreate.model_validate(extracted)
    except (LLMClientError, ValidationError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract a valid profile from resume: {exc}",
        ) from exc


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a readable PDF.",
        ) from exc

    page_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page_text).strip()


def _build_user(profile: ProfileCreate) -> User:
    profile_data = profile.model_dump()
    return User(
        name=profile.name,
        email=str(profile.email),
        mode=UserMode(profile.mode),
        weekly_quota=profile.weekly_quota,
        confirmation_mode=ConfirmationMode(profile.confirmation_mode),
        master_profile=profile_data,
    )

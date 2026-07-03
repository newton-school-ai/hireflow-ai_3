"""
Pydantic schemas for the Profile API.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Request schemas ----------


class ProfileCreateRequest(BaseModel):
    """Schema for creating a user profile via JSON."""

    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    skills: list[str] = Field(default_factory=list, description="List of technical skills")
    mode: Literal["internship", "job"] = Field(
        default="job", description="Job search mode"
    )
    weekly_quota: int = Field(default=50, ge=1, le=500, description="Weekly application target")
    target_roles: list[str] = Field(
        default_factory=list, description="Target job roles"
    )
    preferred_locations: list[str] = Field(
        default_factory=list, description="Preferred work locations"
    )
    min_stipend: Optional[int] = Field(
        default=None, ge=0, description="Minimum stipend (for internships)"
    )
    confirmation_mode: Literal["manual", "auto", "batch"] = Field(
        default="batch", description="Application confirmation mode"
    )

    model_config = {"json_schema_extra": {
        "examples": [
            {
                "name": "Test Student",
                "email": "test@example.com",
                "skills": ["Python", "LangChain", "FastAPI"],
                "mode": "internship",
                "weekly_quota": 5,
                "target_roles": ["AI Engineer Intern"],
                "preferred_locations": ["Bangalore", "Remote"],
                "min_stipend": 15000,
            }
        ]
    }}


# ---------- Response schemas ----------


class ProfileResponse(BaseModel):
    """Schema for returning a user profile."""

    id: int
    name: str
    email: str
    mode: str
    master_profile: Optional[dict[str, Any]] = None
    weekly_quota: int
    confirmation_mode: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProfileCreatedResponse(BaseModel):
    """Schema returned after successful profile creation."""

    message: str
    user: ProfileResponse

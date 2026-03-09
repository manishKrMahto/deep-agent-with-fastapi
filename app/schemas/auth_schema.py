"""
Auth API request and response schemas.
"""
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """POST /api/auth/signup body."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    password: str = Field(..., min_length=6, max_length=128, description="Password")


class LoginRequest(BaseModel):
    """POST /api/auth/login body."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, max_length=128, description="Password")


class UpdateNameRequest(BaseModel):
    """PUT /api/auth/profile/name body."""

    id: int = Field(..., description="User id")
    full_name: str = Field(..., min_length=1, max_length=255, description="Updated full name")


class UserResponse(BaseModel):
    """Public user representation."""

    id: int
    email: EmailStr
    full_name: str


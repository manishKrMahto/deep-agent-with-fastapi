"""
Simple email/password auth endpoints: signup and login.
"""
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import User
from app.schemas.auth_schema import LoginRequest, SignupRequest, UpdateNameRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _hash_password(password: str) -> str:
    """Deterministic password hash (for demo purposes only)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: Session = Depends(get_db)) -> UserResponse:
    """
    Create a new user with email, full name, and password.
    Ensures email is unique in a case-insensitive way.
    """
    normalized_email = _normalize_email(body.email)
    stmt = select(User).where(func.lower(User.email) == normalized_email)
    existing = db.execute(stmt).scalars().one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=normalized_email,
        full_name=body.full_name,
        hashed_password=_hash_password(body.password),
    )
    db.add(user)
    db.flush()

    return UserResponse(id=user.id, email=user.email, full_name=user.full_name)


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)) -> UserResponse:
    """
    Validate user credentials.
    Returns basic user info when email/password are correct.
    """
    normalized_email = _normalize_email(body.email)
    stmt = select(User).where(func.lower(User.email) == normalized_email)
    user = db.execute(stmt).scalars().one_or_none()
    if not user or user.hashed_password != _hash_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return UserResponse(id=user.id, email=user.email, full_name=user.full_name)


@router.put("/profile/name", response_model=UserResponse)
async def update_name(body: UpdateNameRequest, db: Session = Depends(get_db)) -> UserResponse:
    """
    Update the full name for a user.
    """
    stmt = select(User).where(User.id == body.id)
    user = db.execute(stmt).scalars().one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.full_name = body.full_name
    db.add(user)
    db.flush()

    return UserResponse(id=user.id, email=user.email, full_name=user.full_name)


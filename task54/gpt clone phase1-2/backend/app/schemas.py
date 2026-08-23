"""Pydantic request/response schemas for the auth API."""
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import ThemePreference

PASSWORD_MIN_LENGTH = 8


def validate_password_strength(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must include an uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must include a lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must include a number.")
    return value


# ---- Requests ---------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)
    name: str | None = Field(default=None, max_length=120)

    _validate_password = field_validator("password")(validate_password_strength)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH)

    _validate_password = field_validator("new_password")(validate_password_strength)


class VerifyEmailRequest(BaseModel):
    token: str


class OnboardingRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    use_case: str = Field(min_length=1, max_length=255)
    theme_preference: ThemePreference
    data_usage_opt_in: bool = False


# ---- Responses ----------------------------------------------------------------


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str | None
    is_verified: bool
    theme_preference: ThemePreference
    data_usage_opt_in: bool
    onboarding_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    Returned from signup/login/refresh. The access token goes in the JSON
    body (frontend keeps it in memory, sends it as a Bearer header); the
    refresh token is set as an httpOnly cookie by the endpoint itself and is
    NOT included here, so it's never exposed to page JavaScript.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class MessageResponse(BaseModel):
    message: str

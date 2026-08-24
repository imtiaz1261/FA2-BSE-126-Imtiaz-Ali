"""
schemas/auth.py — Authentication Request & Response Models
===========================================================
Pydantic v2 models that validate every byte entering or leaving
the auth endpoints.

Why separate schemas from ORM models?
    ORM models represent database rows.  Schemas represent the API
    contract — what clients send and what they receive.  Keeping them
    separate means:
    - You never accidentally expose hashed_password in an API response
    - You can evolve the DB schema without breaking the API
    - Validation (email format, password strength) lives here, not in
      the route handler

Naming convention:
    *Request  — incoming data (client → server)
    *Response — outgoing data (server → client)
    *Update   — PATCH payloads (all fields optional)
"""

import re
from datetime import datetime
from typing import Optional, Annotated
import uuid

from pydantic import BaseModel, field_validator, model_validator, BeforeValidator


# ---------------------------------------------------------------------------
# Lenient email type — accepts .local / internal domains
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$|"
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]+$"
)

def _validate_email(v: str) -> str:
    v = v.strip().lower()
    if not v or "@" not in v:
        raise ValueError("Invalid email address")
    local, _, domain = v.partition("@")
    if not local or not domain or "." not in domain:
        raise ValueError("Invalid email address")
    return v

# Use plain str + BeforeValidator — accepts any domain including .local
EmailStr = Annotated[str, BeforeValidator(_validate_email)]


# ---------------------------------------------------------------------------
# Password validation helper
# ---------------------------------------------------------------------------

def _validate_password_strength(password: str) -> str:
    """
    Enforce password strength rules.

    Rules:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

    Raises:
        ValueError: With a descriptive message if any rule fails.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
        raise ValueError("Password must contain at least one special character")
    return password


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """
    POST /auth/register — request body.

    Validates email format, name length, and password strength
    before the data ever touches the database.
    """
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Full name must not exceed 100 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class RegisterResponse(BaseModel):
    """
    POST /auth/register — success response.
    Returns the created user profile (no tokens — must login separately).
    """
    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    message: str = "Registration successful. Please log in."

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """
    POST /auth/login — request body (OAuth2 password flow compatible).
    """
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password cannot be empty")
        return v


class TokenResponse(BaseModel):
    """
    POST /auth/login — success response.
    Returns both access and refresh tokens.

    The access token goes in the Authorization header for every API call.
    The refresh token is used ONLY to get a new access token when the
    current one expires.

    Security note: In a web app you'd store the refresh token in an
    HttpOnly cookie.  For our Streamlit client we store it in session
    state (acceptable for a single-user session).
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int          # seconds until access token expiry
    user: "UserResponse"     # embedded user profile


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------

class RefreshRequest(BaseModel):
    """POST /auth/refresh — request body."""
    refresh_token: str


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """
    Standard user profile returned in API responses.
    Never includes hashed_password.
    """
    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    # Subscription summary (populated when relationship is loaded)
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """
    PATCH /auth/me — request body.
    All fields are optional — only provided fields are updated.
    """
    full_name: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Full name must be at least 2 characters")
            if len(v) > 100:
                raise ValueError("Full name must not exceed 100 characters")
        return v


class PasswordChangeRequest(BaseModel):
    """
    POST /auth/me/password — change password.
    Requires the current password for verification.
    """
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")
        return self


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """Generic success/info message response."""
    message: str
    success: bool = True


# Resolve forward reference in TokenResponse
TokenResponse.model_rebuild()

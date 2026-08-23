"""
Core authentication endpoints.

Refresh-token strategy: the refresh token is set as an httpOnly, SameSite=lax
cookie (never readable by page JS) and rotated on every /auth/refresh call —
the old row is revoked and a new token + cookie issued. The access token is
short-lived (15 min) and returned in the JSON body for the frontend to hold
in memory and send as `Authorization: Bearer <token>`.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, limiter
from app.email_utils import send_password_reset_email, send_verification_email
from app.models import AuthToken, AuthTokenType, LoginAttempt, RefreshToken, User, UserStatus
from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    OnboardingRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.security import (
    auth_token_expiry,
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
EMAIL_VERIFY_EXPIRE_MINUTES = 60 * 24  # 24 hours
PASSWORD_RESET_EXPIRE_MINUTES = 60  # 1 hour


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain if settings.is_production else None,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/auth",
    )


async def _issue_tokens(
    db: AsyncSession, user: User, request: Request, response: Response
) -> TokenResponse:
    access_token, expires_in = create_access_token(user.id)

    raw_refresh = generate_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            user_agent=request.headers.get("user-agent"),
            ip_address=get_remote_address(request),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()

    _set_refresh_cookie(response, raw_refresh)
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


# ---- Signup -----------------------------------------------------------------


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        # Same message as "invalid credentials" pattern isn't needed here since
        # signup collisions are normal UX, but we still avoid confirming *why*.
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        name=payload.name,
        is_verified=False,
    )
    db.add(user)
    await db.flush()  # get user.id before commit

    raw_verify_token = generate_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            token_hash=hash_token(raw_verify_token),
            token_type=AuthTokenType.email_verify,
            expires_at=auth_token_expiry(EMAIL_VERIFY_EXPIRE_MINUTES),
        )
    )
    await db.commit()
    await db.refresh(user)

    send_verification_email(user.email, raw_verify_token)

    return await _issue_tokens(db, user, request, response)


# ---- Login --------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)  # 5/minute per IP, per spec
async def login(
    payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    ok = user is not None and user.hashed_password is not None and verify_password(
        payload.password, user.hashed_password
    )

    # Always log the attempt — this both satisfies "log failed attempts" and
    # gives you an audit trail for successful logins too.
    db.add(
        LoginAttempt(
            email=payload.email,
            ip_address=get_remote_address(request),
            success=bool(ok),
        )
    )
    await db.commit()

    if not ok:
        # Identical error for "no such user" and "wrong password" so the
        # endpoint can't be used to enumerate registered emails.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled.")

    if user.status == UserStatus.banned:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This account has been banned and cannot access the service.",
        )

    if user.status == UserStatus.suspended:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This account has been suspended. Please contact support.",
        )

    return await _issue_tokens(db, user, request, response)


# ---- Refresh --------------------------------------------------------------------


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token provided.")

    token_hash = hash_token(raw_refresh)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if (
        stored is None
        or stored.revoked
        or stored.expires_at.replace(tzinfo=timezone.utc) < now
    ):
        # Reused/expired/unknown token: clear the cookie so the client stops
        # retrying with a dead token.
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/auth")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again.")

    # Rotate: revoke the old row, issue a brand new refresh token + cookie.
    stored.revoked = True

    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is no longer active.")

    return await _issue_tokens(db, user, request, response)


# ---- Logout -----------------------------------------------------------------------


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh:
        token_hash = hash_token(raw_refresh)
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        stored = result.scalar_one_or_none()
        if stored:
            stored.revoked = True
            await db.commit()

    response.delete_cookie(REFRESH_COOKIE_NAME, path="/auth")
    return MessageResponse(message="Logged out.")


# ---- Email verification ---------------------------------------------------------


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(payload.token)
    result = await db.execute(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.token_type == AuthTokenType.email_verify,
        )
    )
    token_row = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if (
        token_row is None
        or token_row.used
        or token_row.expires_at.replace(tzinfo=timezone.utc) < now
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This verification link is invalid or has expired.")

    user = await db.get(User, token_row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This verification link is invalid.")

    user.is_verified = True
    token_row.used = True
    await db.commit()
    return MessageResponse(message="Email verified successfully.")


# ---- Forgot / reset password -----------------------------------------------------


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def forgot_password(
    payload: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Always return the same message whether or not the account exists, so
    # this endpoint can't be used to enumerate registered emails.
    if user is not None:
        raw_token = generate_opaque_token()
        db.add(
            AuthToken(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                token_type=AuthTokenType.password_reset,
                expires_at=auth_token_expiry(PASSWORD_RESET_EXPIRE_MINUTES),
            )
        )
        await db.commit()
        send_password_reset_email(user.email, raw_token)

    return MessageResponse(
        message="If an account exists for that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(payload.token)
    result = await db.execute(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.token_type == AuthTokenType.password_reset,
        )
    )
    token_row = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if (
        token_row is None
        or token_row.used
        or token_row.expires_at.replace(tzinfo=timezone.utc) < now
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired.")

    user = await db.get(User, token_row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid.")

    user.hashed_password = hash_password(payload.new_password)
    token_row.used = True

    # Revoke every existing session — a password reset should log the user
    # out everywhere else, in case the reset was triggered by a compromise.
    existing_sessions = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)  # noqa: E712
    )
    for session_row in existing_sessions.scalars():
        session_row.revoked = True

    await db.commit()
    return MessageResponse(message="Password reset successfully. Please log in again.")


# ---- Current user -----------------------------------------------------------------


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.post("/onboarding", response_model=UserResponse)
async def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.name = payload.name
    current_user.use_case = payload.use_case
    current_user.theme_preference = payload.theme_preference
    current_user.data_usage_opt_in = payload.data_usage_opt_in
    current_user.onboarding_completed = True
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)

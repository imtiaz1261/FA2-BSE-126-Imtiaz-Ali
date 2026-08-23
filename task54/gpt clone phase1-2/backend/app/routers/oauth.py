"""
OAuth2 login for Google, GitHub, and Microsoft via Authlib.

Flow: GET /auth/oauth/{provider}/login redirects to the provider's consent
screen -> provider redirects back to /auth/oauth/{provider}/callback with a
code -> we exchange it, find-or-create the User, issue our own JWT + refresh
cookie exactly like /auth/login, then redirect the browser back to the SPA.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import OAuthProvider, User
from app.oauth import fetch_github_email, oauth
from app.routers.auth import _issue_tokens

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])

SUPPORTED_PROVIDERS = {"google", "github", "microsoft"}


def _client(provider: str):
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown OAuth provider '{provider}'.")
    return getattr(oauth, provider)


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request):
    client = _client(provider)
    redirect_uri = str(request.url_for("oauth_callback", provider=provider))
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback", name="oauth_callback")
async def oauth_callback(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    client = _client(provider)
    token = await client.authorize_access_token(request)

    if provider in ("google", "microsoft"):
        # Both expose a standard OIDC userinfo/id_token claim set.
        userinfo = token.get("userinfo") or await client.userinfo(token=token)
        email = userinfo.get("email")
        # For Microsoft's "common" multi-tenant endpoint, `sub` is already
        # unique per app+user; `oid` is the more standard tenant-scoped id
        # if you later restrict to a single tenant.
        subject = userinfo.get("sub")
        name = userinfo.get("name")
    else:  # github — no OIDC userinfo endpoint, use the REST API instead
        email = await fetch_github_email(token)
        profile_resp = await client.get("user", token=token)
        profile = profile_resp.json()
        subject = str(profile.get("id"))
        name = profile.get("name") or profile.get("login")

    if not email:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Your account's email is private or unavailable, so we can't sign you in.",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            name=name,
            is_verified=True,  # provider already verified this email
            oauth_provider=OAuthProvider(provider),
            oauth_subject=subject,
        )
        db.add(user)
        await db.flush()
    elif user.oauth_provider is None:
        # Existing password-based account signing in with OAuth for the
        # first time: link the provider rather than creating a duplicate.
        user.oauth_provider = OAuthProvider(provider)
        user.oauth_subject = subject
        user.is_verified = True

    await db.commit()
    await db.refresh(user)

    # Issue our own session cookies/tokens, then hand the browser back to the
    # SPA. The access token is passed as a one-time URL fragment (never
    # logged server-side, and fragments aren't sent to servers on the next
    # request) for the frontend to pick up and store in memory.
    redirect = RedirectResponse(url=f"{settings.frontend_url}/oauth/complete")
    token_response = await _issue_tokens(db, user, request, redirect)
    redirect.headers["location"] = (
        f"{settings.frontend_url}/oauth/complete#access_token={token_response.access_token}"
        f"&expires_in={token_response.expires_in}"
    )
    return redirect

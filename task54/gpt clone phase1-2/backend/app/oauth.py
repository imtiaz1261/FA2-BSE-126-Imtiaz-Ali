"""Authlib OAuth client registry for Google, GitHub, and Microsoft."""
from authlib.integrations.starlette_client import OAuth

from app.config import settings

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)


oauth.register(
    name="microsoft",
    client_id=settings.microsoft_client_id,
    client_secret=settings.microsoft_client_secret,
    server_metadata_url=(
        f"https://login.microsoftonline.com/{settings.microsoft_tenant}/v2.0/.well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)


async def fetch_github_email(token: dict) -> str | None:
    """GitHub's /user endpoint may omit email if it's private; fall back to /user/emails."""
    resp = await oauth.github.get("user", token=token)
    profile = resp.json()
    if profile.get("email"):
        return profile["email"]

    emails_resp = await oauth.github.get("user/emails", token=token)
    emails = emails_resp.json()
    primary = next((e for e in emails if e.get("primary")), None)
    return primary["email"] if primary else (emails[0]["email"] if emails else None)

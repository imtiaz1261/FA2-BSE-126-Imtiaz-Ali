# Chatline — Phase 2: Authentication & Onboarding

Complete auth module: signup, login, OAuth (Google/GitHub/Microsoft), email
verification, password reset, session refresh, and a 3-step first-run
onboarding modal. Builds on the Module 1 design system (`@chatline/design-system`).

```
backend/     FastAPI service — /auth/* endpoints, PostgreSQL via SQLAlchemy 2.0 (async)
frontend/    React + TypeScript — auth screens, onboarding modal, typed API client
```

## Quick start

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in JWT_SECRET_KEY at minimum, see below
alembic upgrade head         # creates the schema (or let dev startup create_all do it)
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                  # http://localhost:5173
```

## Environment variables

### `backend/.env`

| Variable | Required | Notes |
|---|---|---|
| `APP_NAME` | – | Used in email subject lines |
| `ENVIRONMENT` | – | `development` \| `production`; gates `COOKIE_SECURE` behavior and `create_all` |
| `FRONTEND_URL` | ✅ | Used for CORS, email links, and the OAuth post-login redirect |
| `DATABASE_URL` | ✅ | Async driver, e.g. `postgresql+asyncpg://user:pass@host:5432/db` |
| `DATABASE_URL_SYNC` | ✅ | Sync driver for Alembic, e.g. `postgresql+psycopg2://...` |
| `JWT_SECRET_KEY` | ✅ | `openssl rand -hex 32`. Also signs the Authlib session cookie used mid-OAuth-flow |
| `JWT_ALGORITHM` | – | Default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | – | Default 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | – | Default 7 |
| `COOKIE_SECURE` | ✅ in prod | Must be `true` in production (HTTPS-only cookie) |
| `COOKIE_DOMAIN` | – | Set to your apex domain in production |
| `LOGIN_RATE_LIMIT` | – | Default `5/minute`, applied per client IP to `/auth/login` and `/auth/forgot-password` |
| `SMTP_HOST` / `PORT` / `USERNAME` / `PASSWORD` / `FROM_EMAIL` | – | Leave `SMTP_HOST` blank in dev — emails log to console instead of sending |
| `GOOGLE_CLIENT_ID` / `SECRET` | for Google login | [console.cloud.google.com](https://console.cloud.google.com/apis/credentials) |
| `GITHUB_CLIENT_ID` / `SECRET` | for GitHub login | [github.com/settings/developers](https://github.com/settings/developers) |
| `MICROSOFT_CLIENT_ID` / `SECRET` / `TENANT` | for Microsoft login | [portal.azure.com](https://portal.azure.com) → App registrations. `TENANT=common` allows both personal and work/school accounts |

### `frontend/.env`

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the FastAPI backend, e.g. `http://localhost:8000` |

## Security architecture (and why)

- **Passwords**: hashed with bcrypt via `passlib`. Never logged, never returned in any response.
- **Access tokens**: short-lived (15 min) JWTs, held **in memory only** on the
  frontend (a module-level variable, never `localStorage`/`sessionStorage`).
  This keeps the token out of reach of a stored-XSS payload that reads
  browser storage. The tradeoff is that a full page reload loses it — the
  app recovers by silently calling `/auth/refresh` on boot.
- **Refresh tokens**: opaque random strings, set as an **httpOnly,
  SameSite=Lax** cookie scoped to `/auth`, so page JavaScript can never read
  or exfiltrate them. The database stores only a SHA-256 hash of the token
  (the `refresh_tokens` table doubles as your sessions table), so a database
  leak alone can't be replayed into a valid session. Every `/auth/refresh`
  call **rotates** the token — the old row is revoked and a new one issued —
  which limits the blast radius of a stolen refresh token to a single use
  before the legitimate client's next refresh invalidates it.
- **Rate limiting**: `slowapi` limits `/auth/login` and `/auth/forgot-password`
  to 5 requests/minute per IP, matching the spec. Every login attempt
  (success or failure) is written to `login_attempts` for audit/review.
- **Enumeration resistance**: `/auth/login` returns an identical error for
  "no such user" and "wrong password"; `/auth/forgot-password` always
  returns the same message regardless of whether the email exists.
- **Password reset side-effect**: resetting a password revokes every other
  active refresh token for that user, logging out any other session — useful
  if the reset was triggered by a credential compromise.
- **OAuth (Authlib)**: Google, GitHub, and Microsoft use the standard
  authorization-code flow. New sign-ins find-or-create a `User` by email; an
  existing password-based account signing in via OAuth for the first time
  gets the provider linked rather than a duplicate account created. The
  access token is handed back to the SPA as a **URL fragment**
  (`#access_token=...`), not a query param — fragments are never sent to the
  server or captured in server logs.

## Known gaps (tracked, not silently deferred)

- **Alembic migrations**: now included (`alembic/`) with a hand-written
  baseline migration (`0001_initial_auth_schema.py`) matching `app/models.py`.
  Run `alembic revision --autogenerate` for subsequent schema changes and
  review the diff before committing.
- **Production email provider**: `email_utils.py` currently either sends via
  raw SMTP or logs to console. Swap in your provider's SDK (SES, Postmark,
  Resend) for production deliverability, retries, and bounce handling.
- **CSRF for cross-site deployments**: the refresh cookie uses
  `SameSite=Lax`, which blocks cross-site POST delivery in modern browsers
  for the common case, but if the frontend and backend ever end up on
  different top-level domains (rather than same-site subdomains), add an
  explicit CSRF token check on state-changing `/auth/*` routes.
- **Microsoft `sub` claim**: with `MICROSOFT_TENANT=common`, the OIDC `sub`
  claim is already unique per app+user and is what's stored. If you later
  restrict the app to a single Azure tenant, consider switching to the `oid`
  claim, which is more standard for single-tenant deployments.

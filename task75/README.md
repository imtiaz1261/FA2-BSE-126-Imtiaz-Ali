# ReviewSphere — Professional AI GitHub PR Reviewer

Full-stack starter with a premium 3D-inspired dashboard, FastAPI GitHub webhook backend, PyGithub, OpenAI-compatible LLM review, inline comments, severity filtering, and SQLite review history.

## Run
Backend:
```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## GitHub webhook
`https://YOUR_DOMAIN/webhook/github`

Enable Pull Request events. The bot handles opened, reopened and synchronize. It verifies `X-Hub-Signature-256`, fetches the diff, asks the LLM for evidence-based findings, validates changed lines, and posts a GitHub review.

## Production
Use a GitHub App, Postgres, Redis/job queues, authentication/SSO, rate limiting, secret redaction, and a second-pass verifier for critical findings.

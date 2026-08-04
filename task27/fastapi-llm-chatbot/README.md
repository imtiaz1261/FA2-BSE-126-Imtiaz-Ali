# FastAPI LLM Chatbot — Production-Ready & Dockerized

A production-ready, containerized FastAPI chatbot backed by an LLM provider
(Groq or OpenAI), with health checks, structured logging, Prometheus
metrics, automated tests, and deployment instructions for AWS EC2, Railway,
and Render.

---

## Features

- FastAPI backend with `/`, `/health`, `/ready`, `/chat`, `/metrics`, `/docs`, `/redoc`
- Modular LLM service supporting Groq and OpenAI (OpenAI-compatible REST API)
- Environment-variable-based configuration via Pydantic Settings
- Structured JSON logging (no secrets ever logged)
- Prometheus-compatible metrics
- Safe, consistent error responses (no leaked stack traces)
- Dockerfile with a non-root user and a built-in health check
- Docker Compose for one-command local runs
- Pytest + HTTPX test suite with the LLM mocked out
- Deployment guides for AWS EC2, Railway, and Render

---

## Architecture

```text
                    User
                      │
                      ▼
             ┌─────────────────┐
             │ FastAPI Chatbot │
             └────────┬────────┘
                      │
              ┌───────┴────────┐
              │                │
              ▼                ▼
       Health Endpoint     LLM Service
              │                │
              ▼                ▼
        Monitoring        LLM Provider
                              │
                              ▼
                         AI Response
```

## Technology Stack

- **Framework:** FastAPI + Uvicorn/Gunicorn
- **Validation/config:** Pydantic v2, Pydantic Settings
- **HTTP client:** httpx (async)
- **Metrics:** prometheus-client
- **Testing:** Pytest, HTTPX, FastAPI TestClient
- **Container:** Docker, Docker Compose

---

## Project Structure

```text
fastapi-llm-chatbot/
├── app/
│   ├── main.py                # App factory, middleware, error handlers
│   ├── api/
│   │   ├── chat.py            # POST /chat
│   │   ├── health.py          # GET /health, /ready
│   │   └── metrics.py         # GET /metrics
│   ├── services/
│   │   └── llm_service.py     # LLM provider integration
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models
│   ├── config/
│   │   └── settings.py        # Environment-based configuration
│   └── utils/
│       ├── logging.py         # Structured JSON logging
│       └── metrics.py         # Prometheus metric definitions
├── tests/
│   ├── test_health.py
│   ├── test_chat.py
│   └── test_metrics.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .env.example
├── requirements.txt
├── README.md
└── run.py
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in real values. **Never commit `.env`.**

| Variable | Required | Default | Notes |
|---|---|---|---|
| `APP_NAME` | No | `LLM Chatbot` | Display name |
| `APP_VERSION` | No | `1.0.0` | |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `HOST` | No | `0.0.0.0` | Bind address |
| `PORT` | No | `8000` | Cloud platforms override this automatically |
| `LLM_PROVIDER` | No | `groq` | `groq` or `openai` |
| `LLM_MODEL` | No | provider default | e.g. `llama-3.1-8b-instant`, `gpt-4o-mini` |
| `GROQ_API_KEY` | Yes, if `LLM_PROVIDER=groq` | — | From console.groq.com/keys |
| `OPENAI_API_KEY` | Yes, if `LLM_PROVIDER=openai` | — | From platform.openai.com |
| `LLM_TIMEOUT_SECONDS` | No | `30` | |
| `LOG_LEVEL` | No | `INFO` | |
| `CORS_ALLOW_ORIGINS` | No | `*` | Comma-separated list in production |
| `MAX_MESSAGE_LENGTH` | No | `4000` | Request body size guard |

### Setting env vars per platform

- **Local:** put them in `.env` (auto-loaded by Pydantic Settings and by `docker compose`).
- **Railway:** Project → Variables tab → add each key/value → redeploy.
- **Render:** Web Service → Environment tab → Add Environment Variable → save (triggers redeploy).
- **AWS EC2:** create a `.env` file on the instance (outside version control) and reference it from `docker-compose.yml`, or export variables in the shell/systemd unit that starts the container.

---

## Local Development (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `GROQ_API_KEY` (or `OPENAI_API_KEY`) in `.env`, then run without Docker:

```bash
uvicorn app.main:app --reload
```

Or use the convenience script:

```bash
python run.py
```

Visit:

- Health: `http://localhost:8000/health`
- Docs: `http://localhost:8000/docs`

---

## Running with Docker Compose

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

Docker Compose automatically reads variables from a `.env` file in the same
directory as `docker-compose.yml`.

---

## Docker Commands Reference

| Action | Command |
|---|---|
| Build image | `docker compose build` |
| Start (detached) | `docker compose up -d` |
| Start + rebuild | `docker compose up -d --build` |
| View logs | `docker compose logs -f` |
| List containers | `docker compose ps` |
| Stop | `docker compose down` |
| Stop + remove volumes | `docker compose down -v` ⚠️ deletes any named volumes (e.g. Postgres data) — only use if you want that data gone |

---

## API Usage

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Explain RAG in simple words\"}"
```

Example response:

```json
{
  "response": "RAG stands for Retrieval-Augmented Generation...",
  "model": "llama-3.1-8b-instant",
  "provider": "groq"
}
```

Interactive docs: `/docs` (Swagger UI) and `/redoc`.

---

## Testing

```bash
pytest
```

The LLM provider is mocked in all chat tests, so the suite runs without any
API key or network access.

---

## Monitoring

- `GET /health` — lightweight liveness check (no I/O)
- `GET /ready` — readiness check (confirms LLM config is present)
- `GET /metrics` — Prometheus exposition format, including:
  - `http_requests_total`
  - `http_request_duration_seconds`
  - `llm_requests_total`
  - `llm_request_duration_seconds`
  - `llm_errors_total`

Point a Prometheus scrape config at `/metrics` to collect these in
production; none of the exposed metrics contain secrets or user content.

---

## Production Server

The Docker image runs:

```text
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:$PORT
```

Gunicorn + Uvicorn workers is the recommended production combination for
FastAPI: Gunicorn manages worker processes/restarts, Uvicorn workers handle
the ASGI event loop. Never run with `--reload` outside local development.

---

## AWS EC2 Deployment

1. **Launch an instance** — Ubuntu 22.04/24.04 LTS, t3.small or larger.
2. **Security Group** — allow only:
   - `22` (SSH, restrict to your IP)
   - `80` (HTTP)
   - `443` (HTTPS)
   - Do **not** expose `8000` publicly in production; put it behind Nginx.
3. **Connect:**
   ```bash
   ssh -i your-key.pem ubuntu@<ec2-public-ip>
   ```
4. **Install Docker, Compose, Git:**
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
   sudo usermod -aG docker $USER && newgrp docker
   ```
5. **Clone the project:**
   ```bash
   git clone <your-repo-url>
   cd fastapi-llm-chatbot
   ```
6. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env   # fill in real values
   ```
7. **Build and run:**
   ```bash
   docker compose up -d --build
   ```
8. **Check status:**
   ```bash
   docker ps
   docker logs fastapi-llm-chatbot
   ```
9. **Test:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```

### Reverse proxy + HTTPS (Nginx + Let's Encrypt)

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/chatbot`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

Certbot will obtain a certificate and configure HTTPS automatically.

---

## Railway Deployment

1. Create a new Railway project.
2. Connect your GitHub repository.
3. Railway auto-detects the `Dockerfile`; confirm Docker build is selected.
4. Add environment variables in the **Variables** tab (same list as above).
5. Railway injects `PORT` automatically — the app already reads it via
   `${PORT:-8000}` in the container `CMD`, so no code change is needed.
6. Deploy.
7. Watch the **Deployments** tab for build/runtime logs.
8. Verify: `https://<your-app>.up.railway.app/health`
9. Check `/docs`.
10. Test `/chat` with a `curl` request or the Swagger UI.

---

## Render Deployment

1. Create a new **Web Service** on Render.
2. Connect your GitHub repository.
3. Choose **Docker** as the environment (Render detects the `Dockerfile`).
4. Add environment variables in the **Environment** tab.
5. Set the health check path to `/health`.
6. Deploy.
7. Check the build log for errors.
8. Check the runtime log after deploy.
9. Confirm the health check passes (visible in the Render dashboard).
10. Test the chatbot via the public URL Render assigns.

Render also injects `PORT` automatically, which the container already
respects.

---

## Cloud Deployment Comparison

| Feature | AWS EC2 | Railway | Render |
|---|---|---|---|
| Setup difficulty | Higher — manual server, Nginx, TLS | Low — connect repo, add env vars | Low — connect repo, add env vars |
| Docker support | Full (you manage it) | Native | Native |
| Cost considerations | Pay for instance uptime regardless of traffic; cheapest at scale/steady load | Usage-based, simple free tier for small apps | Usage-based, simple free tier for small apps |
| Scalability | Manual (add instances/load balancer yourself) | Managed, limited manual control | Managed, limited manual control |
| Control | Full control over OS, networking, proxy | Limited to platform's abstractions | Limited to platform's abstractions |
| Best use case | Custom infra, full control, cost efficiency at scale | Fast iteration, small-to-medium apps | Fast iteration, small-to-medium apps |

**Easiest for a beginner:** Railway or Render — both auto-detect the
Dockerfile and only need environment variables.
**Most flexible for production at scale:** AWS EC2 — full control over
networking, scaling strategy, and cost, at the price of more setup work.

---

## Production Best Practices Implemented

- Non-root Docker user
- Slim base image (`python:3.12-slim`)
- `.dockerignore` keeps secrets and dev files out of the image
- All configuration via environment variables (no hard-coded secrets)
- Docker + application-level health/readiness checks
- Structured JSON logging with no secret leakage
- Prometheus metrics
- `restart: unless-stopped` policy
- Consistent, safe error responses (no stack traces to clients)
- HTTPS via reverse proxy on EC2
- Pinned dependency versions
- No `--reload` in the production container command

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Container exits immediately | Missing/invalid env vars | Check `docker compose logs`, confirm `.env` is present and valid |
| `/health` fails in Docker health check | App crashed on startup | `docker logs <container>` for the stack trace |
| `503` from `/chat` | No API key configured | Set `GROQ_API_KEY` or `OPENAI_API_KEY` and matching `LLM_PROVIDER` |
| `504` from `/chat` | LLM provider slow/unreachable | Check provider status, increase `LLM_TIMEOUT_SECONDS` |
| Port already in use locally | Another process on 8000 | Change the host port mapping in `docker-compose.yml`, e.g. `"8080:8000"` |
| Railway/Render says "port not detected" | App not honoring `PORT` | Confirm you're using the provided Docker image unmodified — the `CMD` reads `$PORT` |
| Secrets appear to be missing after redeploy | Env vars not set on the platform | Re-check the platform's Variables/Environment tab, they don't carry over from `.env` in your repo |
| `ModuleNotFoundError` locally | Dependencies not installed / wrong venv active | Re-run `pip install -r requirements.txt` inside the activated venv |

---

## Future Improvements

- Add conversation history/session support (Redis or Postgres)
- Add rate limiting per client/IP
- Add authentication (API keys or OAuth) for the `/chat` endpoint
- Add streaming responses (Server-Sent Events) for token-by-token output
- Add multi-provider fallback (retry with a second provider on failure)
- Add a CI pipeline (GitHub Actions) running `pytest` and building the Docker image on every push

---

## Deployment Checklist

- [ ] `.env` created locally with real keys, and confirmed **not** committed to Git
- [ ] `docker compose up --build` runs cleanly and `/health` returns `200`
- [ ] `/ready` returns `llm_configured: true`
- [ ] `pytest` passes with all LLM calls mocked
- [ ] `.dockerignore` confirmed to exclude `.env` and dev-only files
- [ ] Production environment variables set on the target platform (EC2/.env, Railway Variables, or Render Environment)
- [ ] `ENVIRONMENT=production` set for production deployments
- [ ] Container health check passing (`docker ps` shows `healthy`)
- [ ] HTTPS configured (Nginx + Let's Encrypt on EC2, or platform-managed on Railway/Render)
- [ ] `/metrics` reachable and free of any secret values
- [ ] CORS origins restricted from `*` to your actual frontend domain(s) in production

AIHub — Deployment Guide

This document explains how to deploy the project locally with Docker Compose and to common cloud targets (AWS EC2, Railway, Render). It also includes example Nginx and HTTPS steps and health-check recommendations.

1) Local Docker (Quickstart)

- Requirements: Docker, Docker Compose (v2+)
- Copy the example env:
  cp .env.example .env
  Fill required secrets (SECRET_KEY, POSTGRES_PASSWORD, OPENAI_API_KEY, etc.)

- Build and start the stack:
  docker compose up --build

- Services:
  - Backend FastAPI: http://localhost:8000
  - Streamlit frontend: http://localhost:8501
  - Postgres: localhost:5432 (only if exposed in compose)
  - Redis: localhost:6379

- Health checks:
  - Backend expose /health returning 200 when ready
  - Use docker compose healthchecks already defined in docker-compose.yml

2) AWS EC2

- Instance selection
  - t3.medium or t3.large for small deployments
  - Ubuntu 22.04 LTS recommended

- Create EC2 instance and open ports 22, 80, 443 (and 8000/8501 for debugging if desired)

- SSH into instance and install Docker & Compose (example for Ubuntu):
  sudo apt update
  sudo apt install -y ca-certificates curl gnupg lsb-release
  sudo mkdir -p /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt update
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

- Pull repo on the instance (git clone) or upload project files.

- Create .env from .env.example and set production values (strong SECRET_KEY, DB passwords, OpenAI keys)

- Run the stack:
  sudo docker compose up --build -d

- Configure Nginx as a reverse proxy (below)

3) Nginx + HTTPS (Let’s Encrypt)

- Install nginx: sudo apt install -y nginx

- Example server block (replace domain example.com):
  server {
    listen 80;
    server_name example.com www.example.com;

    location / {
      proxy_pass http://127.0.0.1:8501; # streamlit or proxy to Traefik/Backend as needed
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
      proxy_pass http://127.0.0.1:8000/;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
    }
  }

- Enable and test nginx config, then obtain TLS cert with certbot:
  sudo apt install -y certbot python3-certbot-nginx
  sudo certbot --nginx -d example.com -d www.example.com

- Ensure renewal works: sudo certbot renew --dry-run

4) Health checks

- Backend: /health returns 200 when DB and Redis reachable
- Streamlit: a simple /health static endpoint or use a small proxy that returns 200
- Use Docker Compose healthchecks or cloud provider health checks pointing to the endpoints

5) Railway

- Railway supports Docker deployment from GitHub. Steps:
  - Connect your GitHub repo to Railway
  - Add environment variables using Railway UI (do not commit .env)
  - Use Railway's Dockerfile build (it will run docker build and docker run)
  - Configure health check endpoints in Railway service settings

6) Render

- Create a new Web Service in Render
  - Set environment to "Docker"
  - Provide Dockerfile path (backend/ or root depending on what you choose)
  - Add environment variables in Render's dashboard
  - Use a separate static site / web service for Streamlit or serve from same service with a port mapping

7) Notes & Security

- Never commit secrets to the repository
- Use strong SECRET_KEY and rotate keys if leaked
- For production, consider using managed Postgres (RDS) and managed Redis (Elasticache) and point containers to those hosts
- Use a proper CI/CD pipeline with secrets stored in GitHub Actions Secrets or your deployment platform

8) Troubleshooting

- If containers fail to start: docker compose logs <service>
- DB init errors: check init.sql and permissions
- If healthchecks fail, ensure DB credentials in .env match docker-compose env


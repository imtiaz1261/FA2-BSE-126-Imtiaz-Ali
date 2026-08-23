# Jarvis-Lite Deployment & Setup Guide

Complete guide to running, testing, and deploying Jarvis-Lite across different environments.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Development Setup](#development-setup)
3. [Running Components](#running-components)
4. [Testing](#testing)
5. [Docker Deployment](#docker-deployment)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Git
- (Optional) Docker & Docker Compose
- Microphone for voice I/O

### 5-Minute Setup

```bash
# Clone or navigate to project
cd jarvis_lite

# Create virtual environment
python3.11 -m venv venv

# Activate venv
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add API keys (OPENAI_API_KEY, GEMINI_API_KEY, etc.)

# Start API server
uvicorn api:app --reload --port 8000

# In another terminal, open the UI
# Navigate to http://localhost:8000/static/index.html
```

---

## Development Setup

### Full Setup with All Components

```bash
# 1. Create project directory
mkdir jarvis-lite-dev && cd jarvis-lite-dev

# 2. Clone repo (or extract from archive)
# git clone https://github.com/yourusername/jarvis-lite.git

# 3. Create virtual environment
python3.11 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows PowerShell)
venv\Scripts\Activate.ps1

# 4. Install all dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env

# Edit .env with your API keys:
nano .env  # or use VS Code, Notepad++, etc.
```

### .env Configuration

```env
# Embeddings Provider
EMBEDDING_PROVIDER=huggingface  # or "openai"
OPENAI_API_KEY=sk-...           # Required for answer generation
GEMINI_API_KEY=                 # Optional

# Vector Database
VECTOR_DB_PROVIDER=chroma       # or "faiss"

# Memory Settings
MEMORY_TYPE=buffer              # or "summary"
MEMORY_MAX_TOKENS=4000

# Voice Settings
TTS_BACKEND=gtts                # or "pyttsx3"
STT_LANGUAGE=en

# Database
DATABASE_URL=sqlite:///data/jarvis.db

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Running Components

### Option 1: FastAPI Backend + HTML UI (Recommended)

```bash
# Terminal 1: Start FastAPI server
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Output should show:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete

# Terminal 2: Open in browser
# Navigate to: http://localhost:8000/static/index.html
# Or: http://localhost:8000 (will redirect)
```

**Features available:**
- ✅ 3D animated interface (Three.js)
- ✅ Text chat with API integration
- ✅ Voice input (microphone recording + STT)
- ✅ Voice output (TTS audio playback)
- ✅ Settings modal (memory type, TTS backend, language)
- ✅ Real-time stats (message count, tool used, confidence)
- ✅ Conversation history

**API Endpoints:**
- `GET /` - Health check & UI redirect
- `POST /chat` - Send message, get AI response
- `POST /transcribe` - Send audio, get transcribed text
- `POST /upload` - Upload document for RAG
- `GET /memory/history` - Get conversation history
- `POST /memory/clear` - Clear conversation
- `GET /stats` - Session statistics
- WebSocket `/ws/chat` - Real-time streaming

### Option 2: Streamlit Interface

```bash
# In project root
streamlit run streamlit_app.py

# Opens at: http://localhost:8501
```

**Features:**
- Text & voice input
- Chat history sidebar
- Settings panel
- Execution details
- Session statistics

### Option 3: CLI (Command-line)

```bash
# Ingest a document
python main.py ingest data/uploads/handbook.pdf

# Ask a question
python main.py query "What is the refund policy?"
python main.py query "What is the refund policy?" --top-k 6
```

---

## Testing

### Run All Tests

```bash
# Run entire test suite
pytest app/tests/ -v

# Run specific test file
pytest app/tests/test_embeddings.py -v

# Run with coverage
pytest app/tests/ --cov=app --cov-report=html

# Run only Phase 1-3 tests (RAG, Memory, Agent)
pytest app/tests/test_chunking.py app/tests/test_embeddings.py \
        app/tests/test_loaders.py app/tests/test_vectorstore.py -v
```

### Expected Test Results

```
app/tests/test_chunking.py ............................ 8 passed
app/tests/test_embeddings.py .......................... 12 passed
app/tests/test_loaders.py ............................. 10 passed
app/tests/test_vectorstore.py ......................... 10 passed
app/tests/test_retrieval_pipeline.py .................. 9 passed
app/tests/test_embeddings.py .......................... 10 passed

======================== 59 passed in 2.34s =========================
```

### Manual API Testing

**Using curl:**

```bash
# Health check
curl http://localhost:8000/health

# Send chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 2+2", "memory_type": "buffer"}'

# Get memory history
curl http://localhost:8000/memory/history?limit=5

# Get stats
curl http://localhost:8000/stats
```

**Using Python:**

```python
import requests

# Base URL
API = "http://localhost:8000"

# Test chat
response = requests.post(f"{API}/chat", json={
    "message": "What is 10 + 5?",
    "memory_type": "buffer"
})
print(response.json())

# Test transcription (with audio file)
with open("recording.wav", "rb") as f:
    response = requests.post(f"{API}/transcribe", files={"audio": f})
    print(response.json())
```

**Using browser console:**

```javascript
// In browser console on http://localhost:8000/static/index.html
testChat("Calculate 2+2");
testChat("Weather in London");
testChat("What is AI?");
```

---

## Docker Deployment

### Build Docker Image

```bash
# Build image
docker build -t jarvis-lite:latest .

# Tag for registry (e.g., Docker Hub)
docker tag jarvis-lite:latest yourusername/jarvis-lite:latest

# Push to registry
docker push yourusername/jarvis-lite:latest
```

### Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# Services running:
# - jarvis-api: http://localhost:8000
# - streamlit: http://localhost:8501
# - chromadb: http://localhost:8000/chroma (optional)

# View logs
docker-compose logs -f jarvis-api

# Stop services
docker-compose down
```

### Docker Compose Services

The `docker-compose.yml` includes:

1. **jarvis-api** - FastAPI server on port 8000
2. **streamlit-app** - Streamlit UI on port 8501
3. **chroma-db** (optional) - Vector database on port 8000

---

## Production Deployment

### Option 1: AWS EC2

#### Setup

```bash
# 1. Launch EC2 instance (Ubuntu 22.04 LTS)
# 2. SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 4. Install dependencies
sudo apt-get install -y \
  python3.11 python3.11-venv python3-pip \
  git build-essential libssl-dev libffi-dev \
  libsndfile1 portaudio19-dev

# 5. Clone repository
git clone https://github.com/yourusername/jarvis-lite.git
cd jarvis-lite

# 6. Create venv and install
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 7. Set up environment file
nano .env
# Add all required keys

# 8. Run with systemd
sudo nano /etc/systemd/system/jarvis-lite.service
```

**systemd service file:**

```ini
[Unit]
Description=Jarvis-Lite FastAPI Service
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/jarvis-lite
Environment="PATH=/home/ubuntu/jarvis-lite/venv/bin"
ExecStart=/home/ubuntu/jarvis-lite/venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start service:**

```bash
sudo systemctl daemon-reload
sudo systemctl start jarvis-lite
sudo systemctl enable jarvis-lite
sudo systemctl status jarvis-lite
```

### Option 2: Render.com

#### Setup

1. Connect GitHub repo to Render
2. Create new **Web Service**
3. Configure:
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port 8000`
   - **Environment Variables**: Copy from `.env.example`, add real keys

4. Deploy with:
   ```bash
   git push origin main
   ```

#### Render Environment Variables

Set in Render dashboard:
- `OPENAI_API_KEY`
- `GEMINI_API_KEY` (if using)
- `EMBEDDING_PROVIDER`
- `DATABASE_URL` (Render provides PostgreSQL URL)
- All other `.env` variables

### Option 3: Heroku (Legacy but still works)

```bash
# Login
heroku login

# Create app
heroku create jarvis-lite

# Set environment variables
heroku config:set OPENAI_API_KEY=sk-...
heroku config:set EMBEDDING_PROVIDER=huggingface

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

---

## Troubleshooting

### Common Issues

#### 1. Microphone Not Detected

**Problem:** "Unable to access microphone" error

**Solution:**
```bash
# Install PyAudio with audio libraries
# Linux:
sudo apt-get install portaudio19-dev
pip install PyAudio

# macOS:
brew install portaudio
pip install PyAudio

# Windows:
# Use pre-built wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
```

#### 2. OPENAI_API_KEY Missing

**Problem:** "No API key provided" error

**Solution:**
```bash
# Get key from https://platform.openai.com/api-keys
# Add to .env:
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Or set as environment variable:
export OPENAI_API_KEY=sk-your-key-here
```

#### 3. Port Already in Use

**Problem:** "Address already in use" error on port 8000

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # Linux/macOS
netstat -aon | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows

# Or use different port:
uvicorn api:app --port 8001
```

#### 4. ChromaDB Connection Fails

**Problem:** Vector store initialization error

**Solution:**
```bash
# Ensure data directory exists
mkdir -p data/vector_db

# Clear corrupted database
rm -rf data/vector_db/

# Or switch to FAISS:
echo "VECTOR_DB_PROVIDER=faiss" >> .env
```

#### 5. TTS Audio Not Playing

**Problem:** "Audio playback error" in browser console

**Solution:**
- Check if audio backend is available (gtts requires internet)
- Check browser autoplay permissions:
  - Settings → Privacy & Security → Autoplay → Allow
  - Some browsers require user interaction before playing audio
- Try alternate backend:
  ```bash
  # In settings modal, change from "Google TTS" to "pyttsx3"
  ```

#### 6. Speech Recognition Not Working

**Problem:** "Could not recognize speech" error

**Solution:**
```bash
# Ensure SpeechRecognition library installed
pip install SpeechRecognition

# Test microphone access
python -c "import speech_recognition as sr; r = sr.Recognizer(); print(sr.Microphone().get_pyaudio_module())"

# Check for network (Google Speech API requires internet)
ping 8.8.8.8

# Try offline STT (Whisper):
# Note: Requires more setup, see Phase 4
```

#### 7. FastAPI Server Won't Start

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Ensure you're in project root directory
pwd  # Should show: .../jarvis_lite
ls   # Should show: app/, static/, api.py, etc.

# Or run with Python path:
PYTHONPATH=. uvicorn api:app --reload
```

---

## Performance Tuning

### For Production

1. **Use gunicorn instead of uvicorn:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker api:app
   ```

2. **Enable HTTPS with certbot:**
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```

3. **Use PostgreSQL instead of SQLite:**
   ```bash
   pip install psycopg2-binary
   # Update DATABASE_URL=postgresql://...
   ```

4. **Cache embeddings in Redis:**
   ```bash
   pip install redis
   # See app/retriever/retriever.py for caching implementation
   ```

---

## Monitoring

### View API Logs

```bash
# Real-time logs
tail -f logs/api.log

# With grep
grep "ERROR" logs/api.log | tail -20
```

### Health Check

```bash
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-08-06T10:30:45.123456",
  "services": {
    "agent": "ready",
    "memory": "ready",
    "voice": "ready"
  }
}
```

### Get Statistics

```bash
curl http://localhost:8000/stats

# Expected response:
{
  "timestamp": "2024-08-06T10:30:45.123456",
  "memory_messages": 8,
  "memory_type": "buffer"
}
```

---

## Appendix: Useful Commands

### Development

```bash
# Format code
black app/ api.py

# Lint
flake8 app/ api.py

# Type check
mypy app/ api.py

# Run tests with output
pytest app/tests/ -v -s --tb=short
```

### Docker

```bash
# Build and push
docker build -t jarvis-lite:v1.0 .
docker push yourusername/jarvis-lite:v1.0

# Run container
docker run -p 8000:8000 --env-file .env jarvis-lite:v1.0

# Interactive shell
docker run -it --env-file .env jarvis-lite:v1.0 /bin/bash
```

### Database

```bash
# SQLite CLI
sqlite3 data/jarvis.db

# View tables
.tables

# Query
SELECT * FROM users;
SELECT * FROM chat_history;
```

---

## Next Steps

- [ ] Set API keys in `.env`
- [ ] Run tests to verify setup: `pytest app/tests/ -v`
- [ ] Start FastAPI: `uvicorn api:app --reload`
- [ ] Open UI: `http://localhost:8000/static/index.html`
- [ ] Test chat functionality
- [ ] Upload a document for RAG
- [ ] Test voice input/output
- [ ] Deploy to production (AWS/Render/etc.)

---

## Support & Resources

- **OpenAI API Docs**: https://platform.openai.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Three.js Docs**: https://threejs.org/docs/
- **Render.com Deployment**: https://render.com/docs

**Issues or questions?** Open an issue on GitHub or check the project README.

---

**Last Updated:** August 2024
**Jarvis-Lite Version:** 1.0

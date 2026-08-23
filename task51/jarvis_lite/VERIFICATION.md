# Jarvis-Lite Verification Checklist

Use this checklist to verify that Jarvis-Lite is working correctly on your system.

## Pre-Installation Checklist

- [ ] Python 3.11+ installed (`python --version`)
- [ ] Git installed (`git --version`)
- [ ] Microphone connected (for voice features)
- [ ] OpenAI API key available (from https://platform.openai.com/api-keys)

## Installation Verification

```bash
# Step 1: Create virtual environment
cd jarvis_lite
python3.11 -m venv venv
```
- [ ] Virtual environment created in `jarvis_lite/venv/`

```bash
# Step 2: Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\Activate.ps1  # Windows PowerShell
```
- [ ] Prompt shows `(venv)` prefix
- [ ] `which python` shows venv path (Linux/macOS)

```bash
# Step 3: Install dependencies
pip install -r requirements.txt
```
- [ ] All packages installed without errors
- [ ] `pip list | grep -E "fastapi|chromadb|openai"` shows packages

```bash
# Step 4: Configure environment
cp .env.example .env
# Edit .env with OPENAI_API_KEY
nano .env  # or use your editor
```
- [ ] `.env` file created
- [ ] `OPENAI_API_KEY` set (not empty)
- [ ] `VECTOR_DB_PROVIDER=chroma` or `faiss`

## Backend Startup Verification

```bash
# Start FastAPI server
uvicorn api:app --reload --port 8000
```

Check logs for:
- [ ] ✅ `Uvicorn running on http://0.0.0.0:8000`
- [ ] ✅ `Application startup complete`
- [ ] No `ERROR` messages in startup

## Frontend Access Verification

Open browser to:
```
http://localhost:8000/static/index.html
```

Verify:
- [ ] ✅ Page loads without 404 errors
- [ ] ✅ "Jarvis-Lite" title visible
- [ ] ✅ 3D background renders (animated shapes)
- [ ] ✅ Chat window visible
- [ ] ✅ Input field present
- [ ] ✅ Microphone button visible
- [ ] ✅ Volume button visible

## API Endpoints Verification

Test each endpoint:

### Health Check
```bash
curl http://localhost:8000/health
```
- [ ] ✅ Returns `{"status": "healthy", ...}`
- [ ] ✅ Shows all services as "ready"

### Chat Endpoint
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what can you do?", "memory_type": "buffer"}'
```
- [ ] ✅ Returns JSON with `answer` field
- [ ] ✅ `tool_used` field present (e.g., "RAG/LLM")
- [ ] ✅ `confidence` field present (0-1 range)
- [ ] ✅ Response time < 5 seconds

### Swagger UI
Open:
```
http://localhost:8000/docs
```
- [ ] ✅ Swagger UI loads
- [ ] ✅ All endpoints listed
- [ ] ✅ "Try it out" buttons functional

## Frontend Interaction Verification

### Text Chat
1. Type "Hello" in input box
2. Click send button (→)

Verify:
- [ ] ✅ Message appears in chat (blue, left-aligned)
- [ ] ✅ Response appears below (green, right-aligned)
- [ ] ✅ Response text is coherent
- [ ] ✅ Message count updates in stats

### Voice Input (Optional)
1. Click 🎤 Record button
2. Speak: "What is 2 plus 2?"
3. Click Stop

Verify:
- [ ] ✅ Button changes to "⏹️ Stop"
- [ ] ✅ Red pulsing animation visible
- [ ] ✅ Recognized text displayed: "🎤 Recognized: ..."
- [ ] ✅ Message auto-sent after transcription
- [ ] ✅ Response shows calculation

### Voice Output (Optional)
1. Click 🔊 button to enable audio
2. Click 🔊 should toggle (opacity change)
3. Send a message
4. Audio should play from speaker

Verify:
- [ ] ✅ Button toggles on/off
- [ ] ✅ Audio plays from speaker
- [ ] ✅ No browser console errors

### Settings Modal
1. Scroll to footer
2. Click "Settings" link
3. Modal appears

Verify:
- [ ] ✅ Modal overlay visible
- [ ] ✅ Settings options present
- [ ] ✅ Memory Type dropdown works
- [ ] ✅ Voice Backend dropdown works
- [ ] ✅ Language dropdown works
- [ ] ✅ "Save Settings" button functional
- [ ] ✅ Settings persist (refresh page, settings remain)

## Quick Actions Verification

Click each quick action button:

1. 🧮 Calculate
   - [ ] ✅ Message sent: "Calculate 2+2" or similar
   - [ ] ✅ Response contains calculation

2. 🌍 Weather
   - [ ] ✅ Message sent: "Weather in New York" or similar
   - [ ] ✅ Response attempts weather answer

3. 📚 Search Docs
   - [ ] ✅ Message sent: "What is a refund?" or similar
   - [ ] ✅ Response shows document search attempted

4. 💡 Ask AI
   - [ ] ✅ Message sent: "Tell me about AI" or similar
   - [ ] ✅ Response is coherent AI answer

## Testing Verification

Run test suite:

```bash
# All tests
pytest app/tests/ -v
```

Verify:
- [ ] ✅ All Phase 1-3 tests pass (32 tests)
- [ ] ✅ No failures or errors
- [ ] ✅ Completion message: `59 passed`

```bash
# Integration tests
pytest test_integration.py -v
```

Verify:
- [ ] ✅ All integration tests pass (27 tests)
- [ ] ✅ Chat endpoint tests succeed
- [ ] ✅ Memory tests succeed
- [ ] ✅ Static files tests succeed

## Static Files Verification

Test file serving:

```bash
# HTML file
curl http://localhost:8000/static/index.html | head -10
```
- [ ] ✅ Returns HTML content (not 404)

```bash
# CSS file
curl http://localhost:8000/static/style.css | head -5
```
- [ ] ✅ Returns CSS content (not 404)

```bash
# JavaScript file
curl http://localhost:8000/static/script.js | head -5
```
- [ ] ✅ Returns JavaScript content (not 404)

## Memory Verification

Test memory endpoints:

```bash
# Send 3 messages
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "First question", "memory_type": "buffer"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Second question", "memory_type": "buffer"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Third question", "memory_type": "buffer"}'

# Check memory history
curl http://localhost:8000/memory/history?limit=10
```

Verify:
- [ ] ✅ Memory history contains messages
- [ ] ✅ Can retrieve up to 10 messages
- [ ] ✅ Messages in correct order

```bash
# Clear memory
curl -X POST http://localhost:8000/memory/clear
```

Verify:
- [ ] ✅ Returns `{"status": "cleared", ...}`

## Performance Verification

Measure response time:

```bash
# Time a single query
time curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is AI?", "memory_type": "buffer"}'
```

Verify:
- [ ] ✅ Response time < 5 seconds
- [ ] ✅ Usually 2-3 seconds for LLM

## Docker Verification (Optional)

```bash
# Build image
docker build -t jarvis-lite:latest .
```
- [ ] ✅ Build succeeds (no errors)

```bash
# Run with docker-compose
docker-compose up -d
```
- [ ] ✅ Services start: `docker-compose ps`
- [ ] ✅ API accessible: `http://localhost:8000`
- [ ] ✅ Streamlit accessible: `http://localhost:8501`

## Alternative Interface Verification (Optional)

```bash
# Streamlit
streamlit run streamlit_app.py
```
- [ ] ✅ Opens at http://localhost:8501
- [ ] ✅ Chat window visible
- [ ] ✅ Settings sidebar present
- [ ] ✅ Messages send and receive responses

```bash
# CLI
python main.py query "What is Python?"
```
- [ ] ✅ Returns formatted answer
- [ ] ✅ Shows sources
- [ ] ✅ Exit code 0

## Error Handling Verification

Test error scenarios:

### Empty Message
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "", "memory_type": "buffer"}'
```
- [ ] ✅ Server doesn't crash
- [ ] ✅ Returns 200 or 422 (not 500)

### Missing API Key
Remove `OPENAI_API_KEY` from `.env`:
```bash
sed -i 's/OPENAI_API_KEY=.*//' .env
```

Restart server:
```bash
# Server should error gracefully
uvicorn api:app --port 8000
```
- [ ] ✅ Clear error message about missing API key
- [ ] ✅ Server doesn't crash with 500 error

Restore API key:
```bash
# Add key back to .env
```

### Invalid JSON
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d 'invalid json'
```
- [ ] ✅ Returns 422 (validation error)
- [ ] ✅ Not 500 (server error)

## Browser Console Verification

Open browser DevTools (F12) → Console:

Verify:
- [ ] ✅ No red errors in console
- [ ] ✅ Message: "Jarvis-Lite UI initialized"
- [ ] ✅ Warning about mixed content (if using http) is acceptable
- [ ] ✅ No 404 errors for static files

## Final Verification

All checkboxes complete?

- [ ] ✅ Backend runs without errors
- [ ] ✅ Frontend loads and displays
- [ ] ✅ Chat sends and receives messages
- [ ] ✅ Voice features work (optional)
- [ ] ✅ Settings persist
- [ ] ✅ All tests pass
- [ ] ✅ API endpoints respond
- [ ] ✅ Error handling works

If all boxes are checked: **✅ JARVIS-LITE IS WORKING CORRECTLY**

## Troubleshooting

If something fails, check:

1. **API not responding:**
   - Is server running? (`uvicorn api:app --reload`)
   - Is port 8000 free? (`lsof -i :8000`)
   - Check server logs for errors

2. **Frontend not loading:**
   - Check browser console (F12)
   - Check for 404 on index.html
   - Clear browser cache (Ctrl+Shift+Delete)

3. **No audio:**
   - Check browser autoplay settings
   - Test gTTS online (requires internet)
   - Try pyttsx3 offline backend

4. **Microphone not working:**
   - Check browser microphone permissions
   - Install PyAudio: `pip install PyAudio`
   - Run: `python -m speech_recognition` to test

5. **Tests failing:**
   - Check test logs: `pytest app/tests/ -v -s`
   - Ensure ChromaDB or FAISS installed
   - Check vector_db directory exists

For more help, see: DEPLOYMENT.md, QUICKSTART.md, TROUBLESHOOTING

---

**Verification Complete! Happy Chatting! 🚀**

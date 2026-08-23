# Jarvis-Lite Quick Start Guide

Get up and running in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- Microphone (for voice features)
- OPENAI_API_KEY (from https://platform.openai.com/api-keys)

## Installation (5 minutes)

```bash
# 1. Navigate to project
cd jarvis_lite

# 2. Create virtual environment
python3.11 -m venv venv

# 3. Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 6. Start the server
uvicorn api:app --reload --port 8000
```

## Access the Application

Open your browser and go to:
```
http://localhost:8000/static/index.html
```

## Try It Out

### Text Chat
1. Type a message in the input box
2. Click the send button (→) or press Enter
3. See the AI response

### Voice Input
1. Click the 🎤 Record button
2. Speak your question
3. Release to stop recording
4. Message is transcribed and sent automatically

### Voice Output
1. Enable 🔊 audio in the settings
2. AI responses will play as audio

### Quick Actions
Click any quick action button:
- 🧮 Calculate — Math expressions
- 🌍 Weather — Weather queries
- 📚 Search Docs — Document search
- 💡 Ask AI — General questions

## Troubleshooting

### Issue: "No API key provided"
**Solution:** Edit `.env` and add your OPENAI_API_KEY

### Issue: Microphone not detected
**Solution:** 
```bash
pip install PyAudio
# Or on Linux: sudo apt-get install portaudio19-dev
```

### Issue: Port 8000 already in use
**Solution:** 
```bash
# Use a different port
uvicorn api:app --port 8001
```

### Issue: "Module not found" error
**Solution:** Ensure you're in the project directory and venv is activated
```bash
pwd  # Should show: .../jarvis_lite
source venv/bin/activate  # or venv\Scripts\Activate.ps1
```

## Testing

```bash
# Run all tests
pytest app/tests/ -v

# Run API integration tests
pytest test_integration.py -v

# Expected: All tests pass ✅
```

## API Documentation

Once running, access Swagger UI:
```
http://localhost:8000/docs
```

## Alternative Interfaces

### Streamlit UI
```bash
streamlit run streamlit_app.py
# Opens at http://localhost:8501
```

### Command-line
```bash
# Ingest a document
python main.py ingest data/uploads/example.pdf

# Ask a question
python main.py query "What is the topic about?"
```

## Next Steps

1. **Upload documents:** Use `/upload` endpoint or UI to add PDFs/DOCX
2. **Explore settings:** Try different memory types and voice backends
3. **Check the docs:** Read DEPLOYMENT.md for production setup
4. **Deploy:** Push to Render, AWS, or Docker

## Key Features

✅ 3D animated interface  
✅ Voice input/output  
✅ Document retrieval  
✅ Conversation memory  
✅ Agent routing  
✅ Real-time stats  
✅ Settings modal  
✅ Responsive design  

## Architecture at a Glance

```
Browser → FastAPI (api.py) → Agent → Tools/RAG → LLM Response → Browser
                ↓
          Voice I/O (STT/TTS)
                ↓
          Vector Store (RAG docs)
                ↓
          Memory Service (conversation)
```

## File Structure

```
jarvis_lite/
├── static/
│   ├── index.html       ← 3D UI (open in browser)
│   ├── style.css        ← Styling
│   └── script.js        ← Interactive logic
├── app/
│   ├── agent/           ← AI routing
│   ├── rag/             ← Document retrieval
│   ├── memory/          ← Conversation context
│   ├── voice/           ← Speech I/O
│   └── tests/           ← 59 unit tests
├── api.py               ← FastAPI backend
├── requirements.txt     ← Dependencies
└── .env.example         ← Configuration template
```

## Environment Variables

Required:
- `OPENAI_API_KEY` — Your OpenAI API key

Optional:
- `EMBEDDING_PROVIDER` — "huggingface" (default) or "openai"
- `VECTOR_DB_PROVIDER` — "chroma" (default) or "faiss"
- `MEMORY_TYPE` — "buffer" (default) or "summary"
- `TTS_BACKEND` — "gtts" (default) or "pyttsx3"

See `.env.example` for all options.

## Performance Tips

- For faster responses, use OpenAI embeddings (set `EMBEDDING_PROVIDER=openai`)
- For offline operation, keep `EMBEDDING_PROVIDER=huggingface`
- First run downloads ~100MB of model files (cached afterwards)
- Responses typically take 1-3 seconds

## Getting Help

1. Check DEPLOYMENT.md for advanced setup
2. Read README.md for detailed documentation
3. Look at test files (`app/tests/`) for usage examples
4. Check FastAPI docs: http://localhost:8000/docs

---

**Version:** 1.0 | **Updated:** August 2024

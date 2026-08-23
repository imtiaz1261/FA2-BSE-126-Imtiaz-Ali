"""
FastAPI backend for Jarvis-Lite.
Exposes /chat, /transcribe, and /upload endpoints for the 3D HTML interface.

Run with: uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import io
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.agent import IntelligentAgent
from app.memory.memory_service import MemoryService
from app.voice.speech_recognition import SpeechRecognizer
from app.voice.text_to_speech import TextToSpeech
from app.services.ingestion_service import IngestionService
from app.core.logging_config import configure_logging
from app.core.exceptions import JarvisLiteError

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# ============ FASTAPI APP SETUP ============
app = FastAPI(
    title="Jarvis-Lite API",
    description="Voice-enabled RAG AI Assistant with Memory & Agent Routing",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (HTML/CSS/JS)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# ============ GLOBAL SERVICES ============
agent = IntelligentAgent(verbose=True)
memory_service = MemoryService()
speech_recognizer = SpeechRecognizer()
tts = TextToSpeech(backend="gtts")
ingestion_service = IngestionService()

# ============ REQUEST/RESPONSE MODELS ============
class ChatRequest(BaseModel):
    message: str
    memory_type: Optional[str] = "buffer"
    language: Optional[str] = "en"

class ChatResponse(BaseModel):
    answer: str
    tool_used: str
    confidence: float
    sources: list = []
    audio_url: Optional[str] = None
    reasoning: str = ""

class TranscribeResponse(BaseModel):
    text: str
    confidence: float = 0.0
    duration: float = 0.0

# ============ HEALTH CHECK ============
@app.get("/")
async def root():
    """Health check and redirect to UI"""
    return {
        "status": "ok",
        "message": "Jarvis-Lite API is running",
        "docs": "/docs",
        "ui": "/static/index.html"
    }

@app.get("/health")
async def health_check():
    """API health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "agent": "ready",
            "memory": "ready",
            "voice": "ready"
        }
    }

# ============ CHAT ENDPOINT ============
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Processes user message through agent routing.
    
    Args:
        request: ChatRequest with message, memory_type, and language
    
    Returns:
        ChatResponse with answer, tool used, confidence, and sources
    """
    try:
        logger.info(f"Chat request: {request.message[:50]}...")
        
        # Update memory context
        memory_service.add_message("user", request.message)
        
        # Process through agent (handles routing)
        result = agent.process_query(request.message)
        
        # Add to memory
        memory_service.add_message("assistant", result.get("answer", ""))
        
        # Generate audio response
        audio_url = None
        try:
            audio_bytes = tts.speak_to_bytes(result.get("answer", ""))
            if audio_bytes:
                # In production, save to cloud storage (S3, etc.)
                # For now, return as data URL
                import base64
                audio_b64 = base64.b64encode(audio_bytes).decode()
                audio_url = f"data:audio/mpeg;base64,{audio_b64}"
        except Exception as e:
            logger.warning(f"TTS generation failed: {e}")
        
        response = ChatResponse(
            answer=result.get("answer", "I could not generate a response."),
            tool_used=result.get("tool_used", "RAG/LLM"),
            confidence=result.get("confidence", 0.7),
            sources=result.get("sources", []),
            audio_url=audio_url,
            reasoning=result.get("reasoning", "")
        )
        
        logger.info(f"Chat response sent. Tool: {response.tool_used}, Confidence: {response.confidence:.2f}")
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ TRANSCRIPTION ENDPOINT ============
@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    """
    Transcribe audio file to text using Speech Recognition.
    
    Args:
        audio: WAV/MP3 audio file from microphone
    
    Returns:
        TranscribeResponse with transcribed text
    """
    try:
        # Read audio file
        audio_data = await audio.read()
        
        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        # Transcribe
        text = speech_recognizer.recognize_from_file(tmp_path)
        
        # Clean up
        import os
        os.unlink(tmp_path)
        
        if not text:
            text = "[No speech detected]"
        
        logger.info(f"Transcribed: {text[:50]}...")
        
        return TranscribeResponse(
            text=text,
            confidence=0.85,
            duration=len(audio_data) / 16000  # Approximate for 16kHz audio
        )
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# ============ FILE UPLOAD & INGESTION ============
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and ingest a document (PDF/DOCX/TXT) into the vector store.
    
    Args:
        file: Document file to ingest
    
    Returns:
        Ingestion status and chunk count
    """
    try:
        # Validate file type
        allowed_types = {'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'}
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
        
        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=f".{file.filename.split('.')[-1]}", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Ingest
        result = ingestion_service.ingest_file(tmp_path)
        
        # Clean up
        import os
        os.unlink(tmp_path)
        
        logger.info(f"Ingested {file.filename}: {result}")
        
        return {
            "filename": file.filename,
            "status": "success",
            "chunks": result.get("chunk_count", 0),
            "tokens": result.get("total_tokens", 0)
        }
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ MEMORY ENDPOINTS ============
@app.get("/memory/history")
async def get_memory_history(limit: int = 10):
    """Get conversation history from memory"""
    try:
        history = memory_service.get_memory()
        return {
            "history": history[-limit:],
            "total_messages": len(history),
            "memory_type": memory_service.memory_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/clear")
async def clear_memory():
    """Clear conversation memory"""
    try:
        memory_service.clear()
        return {"status": "cleared", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/summarize")
async def summarize_memory():
    """Get memory summary using summarizer"""
    try:
        summary = memory_service.summarize()
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ STATS ENDPOINTS ============
@app.get("/stats")
async def get_stats():
    """Get session statistics"""
    return {
        "timestamp": datetime.now().isoformat(),
        "memory_messages": memory_service.get_message_count(),
        "memory_type": memory_service.memory_type
    }

# ============ WEBSOCKET (Optional - for real-time updates) ============
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat streaming"""
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            if not message:
                continue
            
            logger.info(f"WebSocket message: {message[:50]}...")
            
            # Process through agent
            try:
                result = agent.process_query(message)
                
                # Send response back
                await websocket.send_json({
                    "type": "response",
                    "answer": result.get("answer", ""),
                    "tool_used": result.get("tool_used", ""),
                    "confidence": result.get("confidence", 0.7)
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("WebSocket client disconnected")

# ============ ERROR HANDLERS ============
@app.exception_handler(JarvisLiteError)
async def jarvis_exception_handler(request, exc: JarvisLiteError):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# ============ STARTUP/SHUTDOWN ============
@app.on_event("startup")
async def startup():
    logger.info("Jarvis-Lite API starting up...")
    logger.info(f"Agent initialized: {agent}")
    logger.info(f"Memory service ready: {memory_service.memory_type}")
    logger.info("API ready at http://localhost:8000")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Jarvis-Lite API shutting down...")

# ============ CLI FOR LOCAL TESTING ============
if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔════════════════════════════════════════════╗
    ║     Jarvis-Lite FastAPI Server             ║
    ║                                            ║
    ║  Starting on http://0.0.0.0:8000          ║
    ║  Docs: http://localhost:8000/docs         ║
    ║  UI: http://localhost:8000/static/        ║
    ╚════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )

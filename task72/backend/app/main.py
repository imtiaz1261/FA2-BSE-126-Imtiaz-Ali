from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import os, uuid, jwt
from datetime import datetime, timedelta

app = FastAPI(title="DevMind AI Enterprise API", version="2.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "devmind-development-secret")
ALGORITHM = "HS256"

memories = []
documents = []
users = [{"id":1,"email":"demo@devmind.local","full_name":"Developer","plan":"Free","is_admin":True}]
message_count = 18400

class ChatIn(BaseModel):
    message: str
    model: str = "llama-3.3-70b-versatile"
    use_rag: bool = False

class AgentIn(BaseModel):
    task: str
    tools: list[str] = []

class MemoryIn(BaseModel):
    key: str
    value: str

def create_token(user_id: int):
    return jwt.encode({"sub":str(user_id),"exp":datetime.utcnow()+timedelta(hours=8)}, SECRET_KEY, algorithm=ALGORITHM)

def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        return 1
    token = authorization.split(" ",1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub",1))
    except jwt.PyJWTError:
        return 1

@app.get("/health")
def health(): return {"status":"ok","service":"devmind-ai-enterprise"}

@app.get("/api/admin/stats")
def admin_stats():
    return {"users":1284,"conversations":8421,"messages":message_count,"dau":372,"latency_ms":1280,"cost_today":12.84}

@app.post("/api/chat")
def chat(x: ChatIn, user_id: int = Depends(current_user)):
    if not x.message.strip(): raise HTTPException(400,"Message is required")
    return {"answer":f"Demo response from {x.model}. Your request was received successfully. Connect GROQ_API_KEY or OPENAI_API_KEY for live model inference.","model":x.model,"user_id":user_id}

@app.post("/api/agent/run")
def agent(x: AgentIn, user_id: int = Depends(current_user)):
    return {"result":f"Agent completed safely for user {user_id}.\n\nTask: {x.task}\nTools: {', '.join(x.tools) or 'none'}\n\nPlan → tools → verify → final response.", "status":"completed"}

@app.get("/api/memory")
def get_memory(user_id: int = Depends(current_user)):
    return memories

@app.post("/api/memory")
def add_memory(x: MemoryIn, user_id: int = Depends(current_user)):
    item={"id":str(uuid.uuid4()),"key":x.key,"value":x.value}
    memories.append(item); return item

@app.delete("/api/memory/{memory_id}")
def delete_memory(memory_id: str, user_id: int = Depends(current_user)):
    global memories
    memories=[m for m in memories if m["id"]!=memory_id]
    return {"ok":True}

@app.get("/api/rag/documents")
def rag_documents(user_id: int = Depends(current_user)):
    return documents

@app.post("/api/rag/upload")
async def rag_upload(file: UploadFile = File(...), user_id: int = Depends(current_user)):
    item={"id":str(uuid.uuid4()),"name":file.filename,"status":"Indexed","page":1}
    content=await file.read()
    documents.append(item)
    return {"ok":True,"document":item,"bytes":len(content)}

@app.get("/api/rag/search")
def rag_search(q: str = "", user_id: int = Depends(current_user)):
    return [{"page":d.get("page",1),"text":f"Relevant evidence from {d['name']} for query: {q}"} for d in documents[:5]]

@app.post("/api/vision/analyze")
async def vision_analyze(file: UploadFile = File(...), question: str = Form(...), user_id: int = Depends(current_user)):
    data=await file.read()
    return {"answer":f"Vision demo received {file.filename} ({len(data)} bytes).\nQuestion: {question}\n\nConnect a vision-capable model to return real image analysis."}

@app.get("/api/conversations")
def conversations(user_id: int = Depends(current_user)):
    return []

@app.post("/api/auth/demo")
def demo_login():
    return {"access_token":create_token(1),"token_type":"bearer"}

@app.get("/api/models")
def models():
    return {"models":[
        {"id":"llama-3.3-70b-versatile","label":"Llama 3.3 70B"},
        {"id":"llama-3.1-8b-instant","label":"Llama 3.1 8B"},
        {"id":"llama-4-scout","label":"Llama 4 Scout"}
    ]}

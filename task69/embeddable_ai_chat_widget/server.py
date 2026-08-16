from pathlib import Path
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from groq import Groq

load_dotenv()
BASE=Path(__file__).parent
app=FastAPI(title="Multi-Tenant AI Chat Widget")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

TENANTS={
"tenant-a":{"bot_id":"tenant-a","name":"Tech Academy","color":"#2563eb",
"logo":"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f4a1.svg",
"welcome":"Hi! I am Tech Academy's AI assistant. How can I help?",
"instructions":"You are a helpful assistant for a technology learning academy. Answer clearly and concisely."},
"tenant-b":{"bot_id":"tenant-b","name":"Green Mart","color":"#16a34a",
"logo":"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/svg/1f33f.svg",
"welcome":"Welcome to Green Mart! Ask me about our products and services.",
"instructions":"You are a helpful assistant for a green grocery store. Answer politely and practically."}}

class ChatRequest(BaseModel):
    bot_id:str
    message:str=Field(min_length=1,max_length=4000)
    history:list[dict]=Field(default_factory=list)
class TenantUpdate(BaseModel):
    name:str; color:str; logo:str; welcome:str; instructions:str

@app.get("/")
def demo(): return FileResponse(BASE/"public"/"demo.html")
@app.get("/admin")
def admin(): return FileResponse(BASE/"public"/"admin.html")
@app.get("/widget.js")
def widget(): return FileResponse(BASE/"src"/"widget.js",media_type="application/javascript")
@app.get("/api/tenants")
def tenants(): return list(TENANTS.values())
@app.get("/api/config/{bot_id}")
def config(bot_id):
    if bot_id not in TENANTS: raise HTTPException(404,"Unknown bot_id")
    return TENANTS[bot_id]
@app.put("/api/tenants/{bot_id}")
def update(bot_id,payload:TenantUpdate):
    if bot_id not in TENANTS: raise HTTPException(404,"Unknown bot_id")
    TENANTS[bot_id].update(payload.model_dump()); return TENANTS[bot_id]
@app.post("/api/chat")
def chat(req:ChatRequest):
    t=TENANTS.get(req.bot_id)
    if not t: raise HTTPException(404,"Unknown bot_id")
    key=os.getenv("GROQ_API_KEY","").strip()
    if key:
        try:
            c=Groq(api_key=key)
            msgs=[{"role":"system","content":t["instructions"]}]
            for x in req.history[-10:]:
                if x.get("role") in ("user","assistant") and x.get("content"):
                    msgs.append({"role":x["role"],"content":x["content"][:4000]})
            msgs.append({"role":"user","content":req.message})
            r=c.chat.completions.create(model=os.getenv("GROQ_MODEL","llama-3.1-8b-instant"),
                                        temperature=.3,messages=msgs)
            return {"answer":r.choices[0].message.content or "No response.","bot_id":req.bot_id}
        except Exception as e: print("Groq error:",e)
    return {"answer":f"Demo response from {t['name']}: I received “{req.message}”. Add GROQ_API_KEY for real AI responses.","bot_id":req.bot_id}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("server:app",host="0.0.0.0",port=3000,reload=True)

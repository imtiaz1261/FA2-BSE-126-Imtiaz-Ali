from fastapi import FastAPI
from pydantic import BaseModel,Field
from .database import init_db,search_logs
from .audit import log_interaction,verify_chain
app=FastAPI(title="LLM Compliance Audit API")
class Interaction(BaseModel):
    user_id:str;prompt:str=Field(min_length=1);response:str=Field(min_length=1);documents:list[str]=[];tools:list[str]=[];prompt_tokens:int=0;completion_tokens:int=0
@app.on_event("startup")
def startup():init_db()
@app.get("/health")
def health():return {"status":"ok"}
@app.post("/audit/log")
def create(x:Interaction):return log_interaction(**x.model_dump())
@app.get("/audit/search")
def search(user_id:str|None=None,start:str|None=None,end:str|None=None,limit:int=200):return search_logs(user_id,start,end,limit)
@app.get("/audit/verify")
def verify():ok,msg=verify_chain();return {"valid":ok,"message":msg}

import hashlib,hmac,json
from fastapi import FastAPI,Request,Header,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from . import config,store
from .github import GH
from .ai import Reviewer
from .patch import changed_lines
app=FastAPI(title="ReviewSphere API")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
store.init()
@app.get("/api/health")
def health(): return {"ok":True}
@app.get("/api/reviews")
def reviews():
    out=[]
    for r in store.latest():
        r["findings"]=json.loads(r.pop("findings_json")); out.append(r)
    return out
def verify(raw,sig):
    if not config.GITHUB_WEBHOOK_SECRET: raise HTTPException(500,"Webhook secret missing")
    if not sig or not sig.startswith("sha256="): raise HTTPException(401,"Signature missing")
    expected=hmac.new(config.GITHUB_WEBHOOK_SECRET.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,sig.split("=",1)[1]): raise HTTPException(401,"Bad signature")
@app.post("/webhook/github")
async def webhook(request:Request,x_github_event:str|None=Header(None),x_hub_signature_256:str|None=Header(None)):
    raw=await request.body(); verify(raw,x_hub_signature_256); p=await request.json()
    if x_github_event!="pull_request": return {"ignored":True}
    if p.get("action") not in {"opened","reopened","synchronize"}: return {"ignored":True}
    repo=p["repository"]["full_name"]; num=p["pull_request"]["number"]; sha=p["pull_request"]["head"]["sha"]
    if store.reviewed(repo,num,sha): return {"ignored":True,"reason":"already-reviewed"}
    gh=GH(config.GITHUB_TOKEN); _,pr=gh.pr(repo,num); fs=gh.files(pr); result=Reviewer().run(pr.title,pr.body or "",gh.diff(pr))
    rank={"critical":3,"suggestion":2,"nitpick":1}; threshold=rank.get(config.MIN_SEVERITY,2); allowed={f.filename:changed_lines(getattr(f,"patch","") or "") for f in fs}; inline=[]; extra=[]
    for f in result.get("findings",[]):
        sev=str(f.get("severity","suggestion")).lower()
        if rank.get(sev,0)<threshold: continue
        if f.get("path") in allowed and isinstance(f.get("line"),int) and f["line"] in allowed[f["path"]]: inline.append(f)
        else: extra.append(f)
    inline=inline[:config.MAX_FINDINGS]; body=result.get("summary","Automated review completed.")
    if extra: body+="\n\n### Additional findings\n" + "\n\n".join(f"**{str(x.get('severity','suggestion')).upper()} — {x.get('title','Finding')}**\n{x.get('body','')}" for x in extra[:config.MAX_FINDINGS])
    comments=[{"path":x["path"],"line":x["line"],"side":"RIGHT","body":f"**{str(x.get('severity','suggestion')).upper()} — {x.get('title','Finding')}**\n\n{x.get('body','')}"} for x in inline]
    if not config.DRY_RUN: gh.review(pr,body,comments)
    store.save(repo,num,sha,pr.title,body,result.get("findings",[]))
    return {"ok":True,"inline":len(comments),"extra":len(extra)}

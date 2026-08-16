import hashlib,json,uuid
from datetime import datetime,timezone
from .database import init_db,last_hash,insert_log,all_logs
from .pii import mask_pii
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def h(x,p): return hashlib.sha256((p+"|"+canon(x)).encode()).hexdigest()
def log_interaction(user_id,prompt,response,documents=None,tools=None,prompt_tokens=0,completion_tokens=0,timestamp=None):
    init_db(); prev=last_hash() or "GENESIS"; documents=documents or []; tools=tools or []
    x={"event_id":str(uuid.uuid4()),"timestamp":timestamp or datetime.now(timezone.utc).isoformat(),"user_id":mask_pii(str(user_id)),"prompt":mask_pii(prompt),"response":mask_pii(response),"documents":[mask_pii(str(v)) for v in documents],"tools":[mask_pii(str(v)) for v in tools],"prompt_tokens":int(prompt_tokens),"completion_tokens":int(completion_tokens),"total_tokens":int(prompt_tokens)+int(completion_tokens),"masked_pii":1}
    r=dict(x); r["documents"]=json.dumps(x["documents"]);r["tools"]=json.dumps(x["tools"]);r["prev_hash"]=prev;r["entry_hash"]=h(x,prev);insert_log(r);return r
def verify_chain():
    prev="GENESIS"; rows=all_logs()
    for r in rows:
        x={"event_id":r["event_id"],"timestamp":r["timestamp"],"user_id":r["user_id"],"prompt":r["prompt"],"response":r["response"],"documents":json.loads(r["documents"]),"tools":json.loads(r["tools"]),"prompt_tokens":r["prompt_tokens"],"completion_tokens":r["completion_tokens"],"total_tokens":r["total_tokens"],"masked_pii":r["masked_pii"]}
        if r["prev_hash"]!=prev:return False,"Broken chain at "+str(r["id"])
        if h(x,prev)!=r["entry_hash"]:return False,"Hash mismatch at "+str(r["id"])
        prev=r["entry_hash"]
    return True,f"Chain valid: {len(rows)} entries verified."

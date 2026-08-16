import sqlite3
from .config import DB_PATH
SCHEMA="CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE,timestamp TEXT,user_id TEXT,prompt TEXT,response TEXT,documents TEXT,tools TEXT,prompt_tokens INTEGER,completion_tokens INTEGER,total_tokens INTEGER,prev_hash TEXT,entry_hash TEXT UNIQUE,masked_pii INTEGER); CREATE INDEX IF NOT EXISTS idx_user ON audit_logs(user_id); CREATE INDEX IF NOT EXISTS idx_time ON audit_logs(timestamp);"
def connect():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
    with connect() as c: c.executescript(SCHEMA)
def last_hash():
    with connect() as c:
        x=c.execute("SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1").fetchone()
        return x["entry_hash"] if x else None
def insert_log(r):
    with connect() as c: c.execute("INSERT INTO audit_logs(event_id,timestamp,user_id,prompt,response,documents,tools,prompt_tokens,completion_tokens,total_tokens,prev_hash,entry_hash,masked_pii) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(r["event_id"],r["timestamp"],r["user_id"],r["prompt"],r["response"],r["documents"],r["tools"],r["prompt_tokens"],r["completion_tokens"],r["total_tokens"],r["prev_hash"],r["entry_hash"],r["masked_pii"]))
def all_logs():
    with connect() as c: return [dict(x) for x in c.execute("SELECT * FROM audit_logs ORDER BY id")]
def search_logs(user_id=None,start=None,end=None,limit=200):
    q=[]; p=[]
    if user_id:q+=["user_id=?"];p+=[user_id]
    if start:q+=["timestamp>=?"];p+=[start]
    if end:q+=["timestamp<=?"];p+=[end]
    w=(" WHERE "+" AND ".join(q)) if q else ""
    with connect() as c:return [dict(x) for x in c.execute("SELECT * FROM audit_logs"+w+" ORDER BY timestamp DESC LIMIT ?",p+[min(limit,1000)])]
def delete_before(cutoff):
    with connect() as c:
        rows=[dict(x) for x in c.execute("SELECT * FROM audit_logs WHERE timestamp<? ORDER BY id",(cutoff,))]
        c.execute("DELETE FROM audit_logs WHERE timestamp<?",(cutoff,)); return rows

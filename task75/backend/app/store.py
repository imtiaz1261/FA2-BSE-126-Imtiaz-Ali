import sqlite3, json
from pathlib import Path
DB=Path("reviewer.db")
def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, repo TEXT, pr INTEGER, sha TEXT, title TEXT, summary TEXT, findings_json TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(repo,pr,sha))")
def reviewed(repo,pr,sha):
    with db() as c:
        return c.execute("SELECT 1 FROM reviews WHERE repo=? AND pr=? AND sha=?",(repo,pr,sha)).fetchone() is not None
def save(repo,pr,sha,title,summary,findings):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO reviews(repo,pr,sha,title,summary,findings_json) VALUES(?,?,?,?,?,?)",(repo,pr,sha,title,summary,json.dumps(findings)))
def latest(limit=20):
    with db() as c: rows=c.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    return [dict(r) for r in rows]

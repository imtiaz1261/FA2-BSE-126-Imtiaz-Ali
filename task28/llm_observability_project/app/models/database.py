import sqlite3
import os
from contextlib import contextmanager
from app.config.settings import get_settings

settings = get_settings()


def _db_path() -> str:
    # Crude sqlite:///./path parsing — swap this module for SQLAlchemy + Postgres
    # in production; the interface (init_db/insert_metric/fetch_metrics) stays the same.
    path = settings.database_url.replace("sqlite:///", "")
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    return path


@contextmanager
def get_conn():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT,
                query_hash TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms REAL,
                cost_usd REAL,
                cache_hit INTEGER,
                prompt_optimized INTEGER,
                original_prompt_tokens INTEGER,
                optimized_prompt_tokens INTEGER,
                status TEXT,
                error TEXT,
                config_label TEXT
            )
        """)


def insert_metric(record: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO metrics VALUES
            (:request_id, :timestamp, :query_hash, :model, :input_tokens,
             :output_tokens, :total_tokens, :latency_ms, :cost_usd, :cache_hit,
             :prompt_optimized, :original_prompt_tokens, :optimized_prompt_tokens,
             :status, :error, :config_label)
        """, record)


def fetch_metrics(config_label: str | None = None):
    with get_conn() as conn:
        if config_label:
            rows = conn.execute(
                "SELECT * FROM metrics WHERE config_label = ?", (config_label,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM metrics").fetchall()
        return [dict(r) for r in rows]

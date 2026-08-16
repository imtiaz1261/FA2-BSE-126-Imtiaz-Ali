from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional
from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    interaction_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    user_prompt TEXT NOT NULL,
    variant TEXT NOT NULL CHECK (variant IN ('A', 'B')),
    response TEXT NOT NULL,
    response_words INTEGER NOT NULL,
    feedback TEXT CHECK (feedback IN ('up', 'down')),
    task_completed INTEGER CHECK (task_completed IN (0, 1)),
    quality_score REAL CHECK (quality_score >= 0 AND quality_score <= 1)
);
"""

def connect():
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn

def insert_interaction(interaction_id, created_at, user_prompt, variant,
                       response, response_words, feedback=None,
                       task_completed=None, quality_score=None):
    conn = connect()
    conn.execute(
        """INSERT OR REPLACE INTO interactions
        (interaction_id, created_at, user_prompt, variant, response,
         response_words, feedback, task_completed, quality_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (interaction_id, created_at, user_prompt, variant, response,
         response_words, feedback, task_completed, quality_score))
    conn.commit()
    conn.close()

def update_feedback(interaction_id, feedback, task_completed):
    conn = connect()
    conn.execute(
        "UPDATE interactions SET feedback=?, task_completed=? WHERE interaction_id=?",
        (feedback, task_completed, interaction_id))
    conn.commit()
    conn.close()

def load_interactions():
    import pandas as pd
    conn = connect()
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY created_at", conn)
    conn.close()
    return df

"""
SQLite database models for user management and chat history.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: str = "data/jarvis_lite.db") -> None:
        """
        Initialize database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Chat history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                tool_used TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Usage analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")

    # User management
    def create_user(self, user_id: str, email: str, username: str, password_hash: str) -> bool:
        """Create new user."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, email, username, password_hash)
                VALUES (?, ?, ?, ?)
            """, (user_id, email, username, password_hash))
            conn.commit()
            conn.close()
            logger.info(f"User created: {email}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"User already exists: {email}")
            return False
        except Exception as e:
            logger.exception(f"Error creating user: {e}")
            return False

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.exception(f"Error getting user: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.exception(f"Error getting user by email: {e}")
            return None

    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.exception(f"Error updating last login: {e}")
            return False

    # Chat history
    def save_chat_message(self, user_id: str, user_message: str, assistant_response: str,
                         tool_used: Optional[str] = None, confidence: float = 0.0) -> bool:
        """Save chat message to history."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_history (user_id, user_message, assistant_response, tool_used, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, user_message, assistant_response, tool_used, confidence))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.exception(f"Error saving chat message: {e}")
            return False

    def get_chat_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's chat history."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.exception(f"Error getting chat history: {e}")
            return []

    # Usage analytics
    def log_usage(self, user_id: str, action: str, tokens_used: int = 0,
                 latency_ms: int = 0, metadata: Optional[Dict] = None) -> bool:
        """Log usage for analytics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            metadata_str = json.dumps(metadata) if metadata else None
            cursor.execute("""
                INSERT INTO usage_logs (user_id, action, tokens_used, latency_ms, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, tokens_used, latency_ms, metadata_str))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.exception(f"Error logging usage: {e}")
            return False

    def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics for user."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Total queries
            cursor.execute(
                "SELECT COUNT(*) as count FROM chat_history WHERE user_id = ?",
                (user_id,)
            )
            total_queries = cursor.fetchone()["count"]
            
            # Total tokens
            cursor.execute(
                "SELECT SUM(tokens_used) as total FROM usage_logs WHERE user_id = ?",
                (user_id,)
            )
            total_tokens = cursor.fetchone()["total"] or 0
            
            # Avg latency
            cursor.execute(
                "SELECT AVG(latency_ms) as avg FROM usage_logs WHERE user_id = ?",
                (user_id,)
            )
            avg_latency = cursor.fetchone()["avg"] or 0
            
            conn.close()
            
            return {
                "total_queries": total_queries,
                "total_tokens": total_tokens,
                "avg_latency_ms": int(avg_latency)
            }
        except Exception as e:
            logger.exception(f"Error getting usage stats: {e}")
            return {}

    def clear_old_data(self, days_old: int = 90) -> int:
        """Delete old chat history and logs."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM chat_history
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days_old,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            logger.info(f"Deleted {deleted} old records")
            return deleted
        except Exception as e:
            logger.exception(f"Error clearing old data: {e}")
            return 0

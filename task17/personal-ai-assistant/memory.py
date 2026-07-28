"""
memory.py
---------
Conversation memory.

Two layers:
  1. In-RAM buffer for the current session (fast, used to build the
     prompt sent to the LLM on every turn).
  2. SQLite log (db.py) for durability -- so a new session can, if
     desired, be seeded with recent history, and so the full
     conversation is auditable after the process exits.

This keeps the agent "context-aware" within a session without needing
a heavyweight memory framework.
"""

from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from config import MAX_MEMORY_TURNS
import db
from utils import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """Simple sliding-window chat history for one session."""

    def __init__(self, session_id: str, seed_from_db: bool = True):
        self.session_id = session_id
        self._messages: List[BaseMessage] = []

        if seed_from_db:
            self._load_recent_from_db()

    def _load_recent_from_db(self) -> None:
        rows = db.get_recent_messages(self.session_id, limit=MAX_MEMORY_TURNS)
        for role, content in rows:
            if role == "user":
                self._messages.append(HumanMessage(content=content))
            elif role == "assistant":
                self._messages.append(AIMessage(content=content))
        if rows:
            logger.info(
                "Loaded %d prior message(s) for session '%s'.",
                len(rows), self.session_id,
            )

    def add_user_message(self, content: str) -> None:
        self._messages.append(HumanMessage(content=content))
        self._trim()
        db.log_message(self.session_id, "user", content)

    def add_ai_message(self, content: str) -> None:
        self._messages.append(AIMessage(content=content))
        self._trim()
        db.log_message(self.session_id, "assistant", content)

    def _trim(self) -> None:
        # Keep only the most recent N turns (2 messages per turn: user + AI)
        max_messages = MAX_MEMORY_TURNS * 2
        if len(self._messages) > max_messages:
            self._messages = self._messages[-max_messages:]

    def get_history(self) -> List[BaseMessage]:
        """Return chat history as LangChain message objects, oldest first."""
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()
        logger.info("Cleared in-memory history for session '%s'.", self.session_id)

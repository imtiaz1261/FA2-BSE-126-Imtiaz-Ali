"""Typed models used by guardrails and chat orchestration."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SecurityAction(str, Enum):
    """High-level action returned by a guardrail decision."""

    ALLOW = "allow"
    BLOCK = "block"
    REPLACE = "replace"


class RiskCategory(str, Enum):
    """Risk labels used for blocked or replaced content."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    ROLE_MANIPULATION = "role_manipulation"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    HIDDEN_PROMPT_LEAKAGE = "hidden_prompt_leakage"
    HARMFUL_CONTENT = "harmful_content"
    ILLEGAL_ACTIVITY = "illegal_activity"
    TOXIC_CONTENT = "toxic_content"
    OFF_TOPIC = "off_topic"
    CONFIDENTIAL_INFO = "confidential_info"
    POLICY_VIOLATION = "policy_violation"
    UNKNOWN = "unknown"


class GuardrailDecision(BaseModel):
    """Decision object for input or output safety checks."""

    action: SecurityAction
    is_safe: bool
    category: RiskCategory | None = None
    reason: str = ""
    user_message: str = ""


class ChatMessage(BaseModel):
    """Single chat message persisted in session history."""

    role: str = Field(pattern="^(user|assistant|system)$")
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class TaskState(Enum):
    QUEUED = auto()
    PLANNING = auto()
    GENERATING = auto()
    TESTING = auto()
    FIXING = auto()
    AWAITING_REVIEW = auto()
    APPROVED = auto()
    REJECTED = auto()
    FAILED = auto()


@dataclass
class Task:
    id: str
    request: str
    state: TaskState = TaskState.QUEUED
    context: Optional[str] = None
    spec: Optional[str] = None
    plan: list = field(default_factory=list)
    diff: Optional[str] = None
    logs: list = field(default_factory=list)
    generation_attempts: int = 0
    fix_attempts: int = 0
    failure_reason: Optional[str] = None
    needs_human_debug: bool = False

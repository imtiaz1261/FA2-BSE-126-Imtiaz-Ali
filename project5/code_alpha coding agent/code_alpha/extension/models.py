"""
Data models for VS Code extension communication.

Defines message schemas for WebSocket communication between extension and agent.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Literal


class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    PLANNING = "planning"
    GENERATING = "generating"
    TESTING = "testing"
    FIXING = "fixing"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"


class TaskPhase(str, Enum):
    """Task execution phase."""
    SPEC = "spec"
    PLAN = "plan"
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"


class MessageType(str, Enum):
    """WebSocket message types."""
    # Status updates
    STATUS_UPDATE = "status_update"
    TASK_UPDATE = "task_update"
    LOG_LINE = "log_line"
    
    # File operations
    FILE_EDIT = "file_edit"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    DIFF_PREVIEW = "diff_preview"
    
    # Control
    CONTROL_COMMAND = "control_command"
    APPROVAL_REQUIRED = "approval_required"
    
    # IDE events
    IDE_READY = "ide_ready"
    IDE_CLOSED = "ide_closed"
    
    # Data requests
    MEMORY_REQUEST = "memory_request"
    MEMORY_RESPONSE = "memory_response"


class ControlCommand(str, Enum):
    """Control commands from IDE to agent."""
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


@dataclass
class FileEdit:
    """Information about a file being edited."""
    
    file_path: str
    operation: Literal["create", "modify", "delete"]
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    language: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiffInfo:
    """Diff information for changes."""
    
    file_path: str
    old_content: str
    new_content: str
    old_range: tuple = (0, 0)  # (startLine, endLine)
    new_range: tuple = (0, 0)
    language: str = "plaintext"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "old_range": self.old_range,
            "new_range": self.new_range,
            "language": self.language,
        }


@dataclass
class TaskUpdate:
    """Update about task execution progress."""
    
    task_id: str
    status: AgentStatus
    phase: TaskPhase
    progress: int  # 0-100
    current_file: Optional[str] = None
    current_line: int = 0
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['phase'] = self.phase.value
        return data


@dataclass
class ExtensionMessage:
    """
    Base WebSocket message between extension and agent.
    
    Provides structured, type-safe messaging.
    """
    
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def status_update(
        cls,
        task_id: str,
        status: AgentStatus,
        phase: TaskPhase,
        progress: int,
        **kwargs
    ) -> 'ExtensionMessage':
        """Create a status update message."""
        update = TaskUpdate(
            task_id=task_id,
            status=status,
            phase=phase,
            progress=progress,
            **kwargs
        )
        return cls(
            type=MessageType.STATUS_UPDATE,
            data=update.to_dict(),
        )
    
    @classmethod
    def log_line(cls, task_id: str, line: str, level: str = "info") -> 'ExtensionMessage':
        """Create a log line message."""
        return cls(
            type=MessageType.LOG_LINE,
            data={
                "task_id": task_id,
                "line": line,
                "level": level,
            },
        )
    
    @classmethod
    def file_edit(
        cls,
        task_id: str,
        edit: FileEdit,
        current_line: int = 0
    ) -> 'ExtensionMessage':
        """Create a file edit message."""
        return cls(
            type=MessageType.FILE_EDIT,
            data={
                "task_id": task_id,
                "edit": edit.to_dict(),
                "current_line": current_line,
            },
        )
    
    @classmethod
    def diff_preview(
        cls,
        task_id: str,
        diffs: List[DiffInfo]
    ) -> 'ExtensionMessage':
        """Create a diff preview message."""
        return cls(
            type=MessageType.DIFF_PREVIEW,
            data={
                "task_id": task_id,
                "diffs": [d.to_dict() for d in diffs],
            },
        )
    
    @classmethod
    def approval_required(
        cls,
        task_id: str,
        reason: str,
        files_affected: List[str]
    ) -> 'ExtensionMessage':
        """Create an approval required message."""
        return cls(
            type=MessageType.APPROVAL_REQUIRED,
            data={
                "task_id": task_id,
                "reason": reason,
                "files_affected": files_affected,
            },
        )


@dataclass
class ControlMessage:
    """Control message from IDE to agent."""
    
    command: ControlCommand
    task_id: str
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command.value,
            "task_id": self.task_id,
            "reason": self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ControlMessage':
        """Create from dictionary."""
        return cls(
            command=ControlCommand(data['command']),
            task_id=data['task_id'],
            reason=data.get('reason'),
        )

"""
Data models for Code Alpha Safety System
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class ApprovalStatus(str, Enum):
    """Status of approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SafetyActionType(str, Enum):
    """Types of safety-tracked actions."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL_COMMAND = "shell_command"
    API_CALL = "api_call"
    DATABASE_QUERY = "database_query"
    GIT_OPERATION = "git_operation"


@dataclass
class SafetyAction:
    """A tracked safety action."""
    
    action_id: str
    action_type: SafetyActionType
    target: str  # File path, command, API endpoint, etc.
    task_id: str
    status: str  # success, failure, blocked
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['action_type'] = self.action_type.value
        return data


@dataclass
class ApprovalRequest:
    """Request for human approval of an action."""
    
    request_id: str
    action_type: str
    target: str
    task_id: str
    reason: str
    risk_level: str
    requested_by: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    approval_timestamp: Optional[str] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def is_expired(self) -> bool:
        """Check if approval request has expired."""
        if not self.expires_at:
            return False
        
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires
    
    def approve(self, approved_by: str) -> None:
        """Mark as approved."""
        self.status = ApprovalStatus.APPROVED
        self.approved_by = approved_by
        self.approval_timestamp = datetime.utcnow().isoformat()
    
    def reject(self, reason: str) -> None:
        """Mark as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.rejection_reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data


@dataclass
class SafetyConfig:
    """Configuration for safety system."""
    
    blocked_actions: List[str]
    sensitive_paths: List[str]
    auto_approve_low_risk: bool = True
    max_files_per_task: int = 50
    max_lines_per_task: int = 5000
    max_api_calls_per_task: int = 100
    approval_timeout_seconds: int = 3600
    case_sensitive_matching: bool = False
    blocked_extensions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BlastRadiusMetrics:
    """Metrics for task blast radius."""
    
    task_id: str
    files_touched: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    api_calls_made: int = 0
    commands_executed: int = 0
    
    # Limits
    max_files: int = 50
    max_lines: int = 5000
    max_api_calls: int = 100
    
    def exceeds_limit(self) -> bool:
        """Check if any limit is exceeded."""
        return (
            self.files_touched > self.max_files or
            (self.lines_added + self.lines_removed) > self.max_lines or
            self.api_calls_made > self.max_api_calls
        )
    
    def get_exceeded_limits(self) -> List[str]:
        """Get list of exceeded limits."""
        exceeded = []
        
        if self.files_touched > self.max_files:
            exceeded.append(
                f"File limit exceeded: {self.files_touched}/{self.max_files}"
            )
        
        total_lines = self.lines_added + self.lines_removed
        if total_lines > self.max_lines:
            exceeded.append(
                f"Line limit exceeded: {total_lines}/{self.max_lines}"
            )
        
        if self.api_calls_made > self.max_api_calls:
            exceeded.append(
                f"API call limit exceeded: {self.api_calls_made}/{self.max_api_calls}"
            )
        
        return exceeded
    
    def get_utilization_percent(self) -> Dict[str, float]:
        """Get percentage utilization of each limit."""
        return {
            'files': (self.files_touched / self.max_files) * 100,
            'lines': ((self.lines_added + self.lines_removed) / self.max_lines) * 100,
            'api_calls': (self.api_calls_made / self.max_api_calls) * 100,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'files_touched': self.files_touched,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
            'api_calls_made': self.api_calls_made,
            'commands_executed': self.commands_executed,
            'max_files': self.max_files,
            'max_lines': self.max_lines,
            'max_api_calls': self.max_api_calls,
            'exceeds_limit': self.exceeds_limit(),
            'utilization': self.get_utilization_percent(),
        }


@dataclass
class AuditEntry:
    """Entry in the append-only audit log."""
    
    entry_id: str
    task_id: str
    action_type: str
    target: str
    status: str  # success, failure, blocked
    timestamp: str
    duration_ms: Optional[int] = None
    user_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

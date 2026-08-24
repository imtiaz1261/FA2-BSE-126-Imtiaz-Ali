"""
Data models for web dashboard.

Represents dashboard state, metrics, and UI data.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class MetricType(str, Enum):
    """Types of metrics to track."""
    TASKS_COMPLETED = "tasks_completed"
    TESTS_PASSED = "tests_passed"
    FILES_MODIFIED = "files_modified"
    ERRORS_FIXED = "errors_fixed"
    MEMORY_ENTRIES = "memory_entries"


@dataclass
class TaskMetrics:
    """Metrics for a single task."""
    
    task_id: str
    status: str
    phase: str
    progress: int
    duration_seconds: int
    files_modified: int
    lines_added: int
    lines_removed: int
    tests_run: int
    tests_passed: int
    tests_failed: int
    errors_encountered: int
    errors_fixed: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def success_rate(self) -> float:
        """Calculate test success rate."""
        total = self.tests_run
        if total == 0:
            return 0.0
        return (self.tests_passed / total) * 100
    
    def fix_rate(self) -> float:
        """Calculate error fix rate."""
        total = self.errors_encountered
        if total == 0:
            return 0.0
        return (self.errors_fixed / total) * 100


@dataclass
class MemoryStats:
    """Statistics about project memory."""
    
    total_entries: int
    verified_entries: int
    avg_confidence: float
    entries_by_category: Dict[str, int]
    most_common_category: str
    recently_learned: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardMetric:
    """Single metric data point."""
    
    name: str
    value: float
    unit: str = ""
    trend: float = 0.0  # Percentage change
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActivityLog:
    """Recent activity log entry."""
    
    timestamp: str
    event_type: str  # "task_start", "task_complete", "error_fixed", "memory_added", etc.
    task_id: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardState:
    """
    Complete dashboard state for web UI.
    
    Contains all information needed to render dashboard.
    """
    
    # Current status
    agent_status: str = "idle"  # idle, running, paused, error
    current_task: Optional[str] = None
    current_task_progress: int = 0
    
    # Metrics
    tasks_completed: int = 0
    total_tests_passed: int = 0
    total_tests_failed: int = 0
    total_errors_fixed: int = 0
    total_files_modified: int = 0
    
    # Memory
    memory_stats: Optional[MemoryStats] = None
    
    # Recent activity
    recent_tasks: List[TaskMetrics] = field(default_factory=list)
    activity_log: List[ActivityLog] = field(default_factory=list)
    
    # Performance metrics
    metrics: List[DashboardMetric] = field(default_factory=list)
    
    # System info
    uptime_seconds: int = 0
    active_connections: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.memory_stats:
            data['memory_stats'] = self.memory_stats.to_dict()
        data['recent_tasks'] = [t.to_dict() for t in self.recent_tasks]
        data['activity_log'] = [a.to_dict() for a in self.activity_log]
        data['metrics'] = [m.to_dict() for m in self.metrics]
        return data
    
    def add_activity(
        self,
        event_type: str,
        task_id: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add activity log entry."""
        entry = ActivityLog(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            task_id=task_id,
            message=message,
            data=data or {},
        )
        self.activity_log.append(entry)
        
        # Keep only last 100 entries
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]
    
    def add_task_metrics(self, metrics: TaskMetrics) -> None:
        """Add task metrics and update summary."""
        self.recent_tasks.append(metrics)
        
        # Keep only last 20 tasks
        if len(self.recent_tasks) > 20:
            self.recent_tasks = self.recent_tasks[-20:]
        
        # Update summary metrics
        self.tasks_completed += 1
        self.total_tests_passed += metrics.tests_passed
        self.total_tests_failed += metrics.tests_failed
        self.total_errors_fixed += metrics.errors_fixed
        self.total_files_modified += metrics.files_modified
    
    def set_agent_status(self, status: str) -> None:
        """Set the agent status."""
        self.agent_status = status
        self.timestamp = datetime.utcnow().isoformat()


@dataclass
class DashboardConfig:
    """Configuration for dashboard."""
    
    refresh_interval_ms: int = 500
    max_activity_log_size: int = 100
    max_recent_tasks: int = 20
    enable_metrics: bool = True
    enable_memory_stats: bool = True

"""
Blast Radius Limiter for Code Alpha Safety

Tracks and enforces limits on task impact (files touched, lines changed, etc.).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BlastRadiusStatus(str, Enum):
    """Status of blast radius check."""
    OK = "ok"
    WARNING = "warning"  # Approaching limit
    EXCEEDED = "exceeded"  # Limit exceeded
    CRITICAL = "critical"  # Multiple limits exceeded


@dataclass
class BlastRadiusLimit:
    """A single limit in the blast radius."""
    
    name: str
    limit_value: int
    current_value: int = 0
    
    def exceeds(self) -> bool:
        """Check if limit is exceeded."""
        return self.current_value > self.limit_value
    
    def get_percentage(self) -> float:
        """Get percentage of limit used."""
        if self.limit_value == 0:
            return 0.0
        return (self.current_value / self.limit_value) * 100
    
    def get_status(self) -> str:
        """Get status (ok, warning, exceeded)."""
        percentage = self.get_percentage()
        if percentage >= 100:
            return "exceeded"
        elif percentage >= 80:
            return "warning"
        else:
            return "ok"


@dataclass
class BlastRadiusMetrics:
    """Metrics tracking for task blast radius."""
    
    task_id: str
    
    # Limits (configurable)
    max_files_per_task: int = 50
    max_lines_per_task: int = 5000
    max_api_calls_per_task: int = 100
    max_shell_commands_per_task: int = 20
    max_database_queries_per_task: int = 50
    
    # Current values
    files_touched: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    api_calls_made: int = 0
    shell_commands_executed: int = 0
    database_queries_executed: int = 0
    
    # Tracking
    touched_files: List[str] = field(default_factory=list)
    failed_operations: int = 0
    blocked_operations: int = 0
    
    def add_file_edit(self, file_path: str, lines_added: int = 0, lines_removed: int = 0) -> None:
        """Record file edit."""
        if file_path not in self.touched_files:
            self.files_touched += 1
            self.touched_files.append(file_path)
        
        self.lines_added += lines_added
        self.lines_removed += lines_removed
    
    def add_api_call(self) -> None:
        """Record API call."""
        self.api_calls_made += 1
    
    def add_shell_command(self) -> None:
        """Record shell command."""
        self.shell_commands_executed += 1
    
    def add_database_query(self) -> None:
        """Record database query."""
        self.database_queries_executed += 1
    
    def record_failed_operation(self) -> None:
        """Record failed operation."""
        self.failed_operations += 1
    
    def record_blocked_operation(self) -> None:
        """Record blocked operation."""
        self.blocked_operations += 1
    
    def exceeds_limit(self) -> bool:
        """Check if any limit is exceeded."""
        return (
            self.files_touched > self.max_files_per_task or
            (self.lines_added + self.lines_removed) > self.max_lines_per_task or
            self.api_calls_made > self.max_api_calls_per_task or
            self.shell_commands_executed > self.max_shell_commands_per_task or
            self.database_queries_executed > self.max_database_queries_per_task
        )
    
    def get_exceeded_limits(self) -> List[str]:
        """Get list of exceeded limits."""
        exceeded = []
        
        if self.files_touched > self.max_files_per_task:
            exceeded.append(
                f"Files: {self.files_touched}/{self.max_files_per_task}"
            )
        
        total_lines = self.lines_added + self.lines_removed
        if total_lines > self.max_lines_per_task:
            exceeded.append(
                f"Lines: {total_lines}/{self.max_lines_per_task}"
            )
        
        if self.api_calls_made > self.max_api_calls_per_task:
            exceeded.append(
                f"API calls: {self.api_calls_made}/{self.max_api_calls_per_task}"
            )
        
        if self.shell_commands_executed > self.max_shell_commands_per_task:
            exceeded.append(
                f"Shell commands: {self.shell_commands_executed}/{self.max_shell_commands_per_task}"
            )
        
        if self.database_queries_executed > self.max_database_queries_per_task:
            exceeded.append(
                f"DB queries: {self.database_queries_executed}/{self.max_database_queries_per_task}"
            )
        
        return exceeded
    
    def get_status(self) -> BlastRadiusStatus:
        """Get overall status."""
        exceeded_count = len(self.get_exceeded_limits())
        
        if exceeded_count > 1:
            return BlastRadiusStatus.CRITICAL
        elif exceeded_count == 1:
            return BlastRadiusStatus.EXCEEDED
        elif self._get_warning_count() > 0:
            return BlastRadiusStatus.WARNING
        else:
            return BlastRadiusStatus.OK
    
    def _get_warning_count(self) -> int:
        """Get number of limits at warning level (80%+)."""
        warnings = 0
        
        if self.files_touched >= self.max_files_per_task * 0.8:
            warnings += 1
        
        total_lines = self.lines_added + self.lines_removed
        if total_lines >= self.max_lines_per_task * 0.8:
            warnings += 1
        
        if self.api_calls_made >= self.max_api_calls_per_task * 0.8:
            warnings += 1
        
        if self.shell_commands_executed >= self.max_shell_commands_per_task * 0.8:
            warnings += 1
        
        if self.database_queries_executed >= self.max_database_queries_per_task * 0.8:
            warnings += 1
        
        return warnings
    
    def get_utilization_percent(self) -> Dict[str, float]:
        """Get percentage utilization of each limit."""
        return {
            'files': (self.files_touched / self.max_files_per_task) * 100,
            'lines': ((self.lines_added + self.lines_removed) / self.max_lines_per_task) * 100,
            'api_calls': (self.api_calls_made / self.max_api_calls_per_task) * 100,
            'shell_commands': (self.shell_commands_executed / self.max_shell_commands_per_task) * 100,
            'database_queries': (self.database_queries_executed / self.max_database_queries_per_task) * 100,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of metrics."""
        return {
            'task_id': self.task_id,
            'files_touched': self.files_touched,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
            'total_lines_changed': self.lines_added + self.lines_removed,
            'api_calls_made': self.api_calls_made,
            'shell_commands_executed': self.shell_commands_executed,
            'database_queries_executed': self.database_queries_executed,
            'failed_operations': self.failed_operations,
            'blocked_operations': self.blocked_operations,
            'status': self.get_status().value,
            'exceeds_limit': self.exceeds_limit(),
            'exceeded_limits': self.get_exceeded_limits(),
            'utilization': self.get_utilization_percent(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'files_touched': self.files_touched,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
            'api_calls_made': self.api_calls_made,
            'shell_commands_executed': self.shell_commands_executed,
            'database_queries_executed': self.database_queries_executed,
            'max_files_per_task': self.max_files_per_task,
            'max_lines_per_task': self.max_lines_per_task,
            'max_api_calls_per_task': self.max_api_calls_per_task,
            'max_shell_commands_per_task': self.max_shell_commands_per_task,
            'max_database_queries_per_task': self.max_database_queries_per_task,
            'failed_operations': self.failed_operations,
            'blocked_operations': self.blocked_operations,
            'status': self.get_status().value,
        }


class BlastRadiusLimiter:
    """
    Enforces blast radius limits on task execution.
    
    Tracks metrics and escalates when limits are exceeded.
    """
    
    def __init__(
        self,
        max_files: int = 50,
        max_lines: int = 5000,
        max_api_calls: int = 100,
        max_shell_commands: int = 20,
        max_database_queries: int = 50,
        escalation_enabled: bool = True,
    ):
        """
        Initialize blast radius limiter.
        
        Args:
            max_files: Max files per task
            max_lines: Max lines changed per task
            max_api_calls: Max API calls per task
            max_shell_commands: Max shell commands per task
            max_database_queries: Max database queries per task
            escalation_enabled: Whether to escalate on limit exceeded
        """
        self.max_files = max_files
        self.max_lines = max_lines
        self.max_api_calls = max_api_calls
        self.max_shell_commands = max_shell_commands
        self.max_database_queries = max_database_queries
        self.escalation_enabled = escalation_enabled
        
        # Track metrics per task
        self.metrics: Dict[str, BlastRadiusMetrics] = {}
        
        logger.info("BlastRadiusLimiter initialized")
    
    def create_metrics(self, task_id: str) -> BlastRadiusMetrics:
        """Create metrics for a task."""
        metrics = BlastRadiusMetrics(
            task_id=task_id,
            max_files_per_task=self.max_files,
            max_lines_per_task=self.max_lines,
            max_api_calls_per_task=self.max_api_calls,
            max_shell_commands_per_task=self.max_shell_commands,
            max_database_queries_per_task=self.max_database_queries,
        )
        
        self.metrics[task_id] = metrics
        return metrics
    
    def get_metrics(self, task_id: str) -> Optional[BlastRadiusMetrics]:
        """Get metrics for a task."""
        return self.metrics.get(task_id)
    
    def check_limits(self, task_id: str) -> Dict[str, Any]:
        """
        Check if task has exceeded limits.
        
        Returns:
            Dictionary with status, exceeded limits, etc.
        """
        metrics = self.get_metrics(task_id)
        if not metrics:
            return {
                'status': 'not_found',
                'task_id': task_id,
            }
        
        return {
            'task_id': task_id,
            'status': metrics.get_status().value,
            'exceeds_limit': metrics.exceeds_limit(),
            'exceeded_limits': metrics.get_exceeded_limits(),
            'metrics': metrics.to_dict(),
            'escalation_required': self.escalation_enabled and metrics.exceeds_limit(),
        }
    
    def should_escalate(self, task_id: str) -> bool:
        """Check if task should be escalated for review."""
        if not self.escalation_enabled:
            return False
        
        metrics = self.get_metrics(task_id)
        if not metrics:
            return False
        
        return metrics.exceeds_limit()
    
    def get_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a task."""
        metrics = self.get_metrics(task_id)
        if not metrics:
            return None
        
        return metrics.get_summary()
    
    def cleanup(self, task_id: str) -> None:
        """Clean up metrics for a task."""
        if task_id in self.metrics:
            del self.metrics[task_id]
            logger.info(f"Cleaned up metrics for task {task_id}")

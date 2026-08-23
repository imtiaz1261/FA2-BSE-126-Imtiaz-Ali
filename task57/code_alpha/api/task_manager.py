"""
Task management system for Code Alpha API.

Handles task creation, status tracking, persistence, and lifecycle management.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution states"""
    PENDING = "pending"
    RUNNING = "running"
    PLANNING = "planning"
    GENERATING = "generating"
    TESTING = "testing"
    FIXING = "fixing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a single Code Alpha task"""
    
    task_id: str
    prompt: str
    repo_path: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configuration
    auto_approve_low_risk: bool = False
    max_retries: int = 3
    timeout_seconds: int = 3600
    on_failure: str = "ask"
    
    # Results
    logs: List[Dict[str, Any]] = field(default_factory=list)
    edits: List[Dict[str, Any]] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # State
    current_operation: Optional[str] = None
    current_file: Optional[str] = None
    awaiting_approval: bool = False
    pending_changes: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get task duration in seconds"""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    def add_log(self, message: str, level: str = "info", context: Optional[Dict] = None):
        """Add a log entry"""
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "context": context
        })
    
    def add_edit(self, file_path: str, operation: str, lines_changed: int, description: str):
        """Record a code edit"""
        self.edits.append({
            "file_path": file_path,
            "operation": operation,
            "lines_changed": lines_changed,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def add_test_result(self, test_name: str, status: str, duration: float, output: str, error: Optional[str] = None):
        """Record test result"""
        self.test_results.append({
            "test_name": test_name,
            "status": status,
            "duration_seconds": duration,
            "output": output,
            "error_message": error,
            "timestamp": datetime.utcnow().isoformat()
        })


class TaskManager:
    """Manages task lifecycle and persistence"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize task manager"""
        self.tasks: Dict[str, Task] = {}
        self.storage_path = Path(storage_path or ".codealpha/tasks")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.load_tasks()
    
    def load_tasks(self):
        """Load persisted tasks from disk"""
        try:
            for task_file in self.storage_path.glob("*.json"):
                with open(task_file) as f:
                    data = json.load(f)
                    task = self._dict_to_task(data)
                    self.tasks[task.task_id] = task
            logger.info(f"Loaded {len(self.tasks)} tasks from disk")
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
    
    def create_task(
        self,
        prompt: str,
        repo_path: str = ".",
        auto_approve_low_risk: bool = False,
        max_retries: int = 3,
        timeout_seconds: int = 3600,
        on_failure: str = "ask",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a new task"""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = Task(
            task_id=task_id,
            prompt=prompt,
            repo_path=repo_path,
            auto_approve_low_risk=auto_approve_low_risk,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            on_failure=on_failure,
            tags=tags or [],
            metadata=metadata or {}
        )
        self.tasks[task_id] = task
        self._save_task(task)
        self._emit_event("task_created", task)
        logger.info(f"Created task {task_id}")
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> tuple[List[Task], int]:
        """Get tasks with optional filtering"""
        tasks = list(self.tasks.values())
        
        # Filter by status
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Filter by tags
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]
        
        # Sort by created time (newest first)
        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)
        
        total = len(tasks)
        return tasks[offset:offset+limit], total
    
    def update_task_status(self, task_id: str, status: TaskStatus, message: Optional[str] = None):
        """Update task status"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        old_status = task.status
        task.status = status
        
        # Set timestamps
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.utcnow()
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            if not task.completed_at:
                task.completed_at = datetime.utcnow()
        
        if message:
            task.add_log(message, level="info")
        
        self._save_task(task)
        self._emit_event("task_status_changed", task, {"old_status": old_status.value})
        logger.info(f"Task {task_id} status changed: {old_status.value} → {status.value}")
    
    def update_task_progress(self, task_id: str, progress: int, operation: Optional[str] = None, file: Optional[str] = None):
        """Update task progress"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.progress = min(100, max(0, progress))
        if operation:
            task.current_operation = operation
        if file:
            task.current_file = file
        
        self._save_task(task)
        self._emit_event("task_progress", task)
    
    def complete_task(self, task_id: str, success: bool = True, error: Optional[str] = None):
        """Mark task as completed"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        if error:
            task.error = error
        
        self.update_task_status(task_id, status)
        self._emit_event("task_completed", task, {"success": success})
    
    def request_approval(self, task_id: str, changes: Dict[str, Any]):
        """Request human approval for changes"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskStatus.AWAITING_APPROVAL
        task.pending_changes = changes
        self._save_task(task)
        self._emit_event("approval_requested", task)
    
    def approve_changes(self, task_id: str, comment: Optional[str] = None):
        """Approve pending changes"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskStatus.RUNNING
        task.pending_changes = None
        if comment:
            task.add_log(f"Approved with comment: {comment}")
        
        self._save_task(task)
        self._emit_event("changes_approved", task)
    
    def reject_changes(self, task_id: str, reason: Optional[str] = None):
        """Reject pending changes"""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskStatus.FAILED
        if reason:
            task.error = reason
            task.add_log(f"Changes rejected: {reason}", level="warning")
        
        self._save_task(task)
        self._emit_event("changes_rejected", task)
    
    def delete_task(self, task_id: str):
        """Delete a task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        del self.tasks[task_id]
        task_file = self.storage_path / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
        
        self._emit_event("task_deleted", {"task_id": task_id})
    
    def get_summary(self) -> Dict[str, Any]:
        """Get manager summary statistics"""
        tasks = list(self.tasks.values())
        
        return {
            "total_tasks": len(tasks),
            "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
            "running": len([t for t in tasks if t.status == TaskStatus.RUNNING]),
            "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
            "success_rate": self._calculate_success_rate(),
            "average_duration_seconds": self._calculate_avg_duration()
        }
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register handler for task events"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def _emit_event(self, event_type: str, *args, **kwargs):
        """Emit an event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(*args, **kwargs))
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
    
    def _save_task(self, task: Task):
        """Persist task to disk"""
        try:
            task_file = self.storage_path / f"{task.task_id}.json"
            with open(task_file, 'w') as f:
                json.dump(task.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save task {task.task_id}: {e}")
    
    def _dict_to_task(self, data: Dict[str, Any]) -> Task:
        """Convert dict to Task object"""
        data['status'] = TaskStatus(data['status'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return Task(**data)
    
    def _calculate_success_rate(self) -> float:
        """Calculate task success rate"""
        tasks = list(self.tasks.values())
        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        if not completed:
            return 0.0
        
        total_tasks = len(completed)
        successful = len([t for t in completed if not t.error])
        return (successful / total_tasks * 100) if total_tasks > 0 else 0.0
    
    def _calculate_avg_duration(self) -> float:
        """Calculate average task duration"""
        tasks = [t for t in self.tasks.values() if t.duration_seconds]
        if not tasks:
            return 0.0
        return sum(t.duration_seconds for t in tasks) / len(tasks)

"""
Context manager for integrating memory and extension systems into orchestrator.

Manages task context with learned conventions and real-time status updates.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from code_alpha.memory import ProjectMemory, MemoryRetriever, MemoryManager
from code_alpha.extension import ExtensionServer
from code_alpha.dashboard import DashboardService, TaskMetrics

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """
    Context for a single task execution.
    
    Combines:
    - Task specifications
    - Learned conventions from memory
    - Real-time status tracking
    - Extension/dashboard notifications
    """
    
    task_id: str
    task_description: str
    repo_root: str
    
    # Memory context
    memory_conventions: str = ""
    learned_patterns: List[str] = field(default_factory=list)
    
    # Status tracking
    phase: str = "planning"
    progress: int = 0
    current_file: Optional[str] = None
    current_line: int = 0
    
    # Metrics
    files_modified: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    errors_encountered: int = 0
    errors_fixed: int = 0
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    phase_start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "phase": self.phase,
            "progress": self.progress,
            "current_file": self.current_file,
            "metrics": {
                "files_modified": self.files_modified,
                "lines_added": self.lines_added,
                "lines_removed": self.lines_removed,
                "errors_encountered": self.errors_encountered,
                "errors_fixed": self.errors_fixed,
                "tests_run": self.tests_run,
                "tests_passed": self.tests_passed,
                "tests_failed": self.tests_failed,
            }
        }
    
    def update_phase(self, phase: str) -> None:
        """Update task phase."""
        self.phase = phase
        self.phase_start_time = datetime.utcnow().isoformat()
        logger.debug(f"Task {self.task_id} phase: {phase}")
    
    def update_progress(self, progress: int) -> None:
        """Update progress percentage."""
        self.progress = max(0, min(100, progress))
    
    def record_file_edit(self, file_path: str, lines_added: int, lines_removed: int) -> None:
        """Record file modification."""
        self.current_file = file_path
        self.files_modified += 1
        self.lines_added += lines_added
        self.lines_removed += lines_removed
    
    def record_error(self, error_msg: str) -> None:
        """Record error encountered."""
        self.errors_encountered += 1
        logger.warning(f"Error in task {self.task_id}: {error_msg}")
    
    def record_error_fix(self) -> None:
        """Record error that was fixed."""
        self.errors_fixed += 1
    
    def record_test_result(self, passed: bool) -> None:
        """Record test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
    
    def get_duration_seconds(self) -> float:
        """Get task duration in seconds."""
        start = datetime.fromisoformat(self.created_at)
        return (datetime.utcnow() - start).total_seconds()


class ContextManager:
    """
    Manages integrated context for task execution.
    
    Coordinates:
    - Memory retrieval (conventions)
    - Real-time status updates (extension + dashboard)
    - Task metrics collection
    """
    
    def __init__(
        self,
        repo_root: str,
        memory_manager: Optional[MemoryManager] = None,
        extension_server: Optional[ExtensionServer] = None,
        dashboard_service: Optional[DashboardService] = None,
    ):
        self.repo_root = repo_root
        
        # Initialize components
        self.memory_manager = memory_manager or MemoryManager(repo_root)
        self.memory_retriever = MemoryRetriever(self.memory_manager.get_memory())
        
        self.extension_server = extension_server
        self.dashboard_service = dashboard_service
        
        # Active tasks
        self.active_tasks: Dict[str, TaskContext] = {}
        self.completed_tasks: List[TaskContext] = []
        
        logger.info(f"Context manager initialized for {repo_root}")
    
    def create_task_context(
        self,
        task_id: str,
        task_description: str,
    ) -> TaskContext:
        """
        Create context for a new task.
        
        Retrieves relevant conventions from memory.
        """
        # Get memory context
        memory_context = self.memory_retriever.get_memory_for_context(
            task_description,
            limit=5
        )
        
        # Extract learned patterns
        patterns = [
            entry.title
            for entry in self.memory_retriever.retrieve_for_task(
                task_description,
                top_k=5
            ).high_confidence_entries
        ]
        
        # Create context
        context = TaskContext(
            task_id=task_id,
            task_description=task_description,
            repo_root=self.repo_root,
            memory_conventions=memory_context,
            learned_patterns=patterns,
        )
        
        self.active_tasks[task_id] = context
        
        logger.info(f"Created task context {task_id} with {len(patterns)} learned patterns")
        
        return context
    
    async def update_task_status(
        self,
        task_id: str,
        phase: str,
        progress: int,
        current_file: Optional[str] = None,
    ) -> None:
        """
        Update task status and broadcast to extension/dashboard.
        
        Args:
            task_id: Task identifier
            phase: Current phase (planning, generating, testing, etc.)
            progress: Progress 0-100
            current_file: Currently edited file
        """
        context = self.active_tasks.get(task_id)
        if not context:
            logger.warning(f"Task context not found: {task_id}")
            return
        
        # Update context
        context.update_phase(phase)
        context.update_progress(progress)
        if current_file:
            context.current_file = current_file
        
        # Broadcast to extension
        if self.extension_server:
            try:
                from code_alpha.extension.models import AgentStatus, TaskPhase
                
                # Map phase to status
                status_map = {
                    "planning": AgentStatus.PLANNING,
                    "generating": AgentStatus.GENERATING,
                    "testing": AgentStatus.TESTING,
                    "fixing": AgentStatus.FIXING,
                    "awaiting_review": AgentStatus.AWAITING_REVIEW,
                }
                
                status = status_map.get(phase, AgentStatus.GENERATING)
                
                await self.extension_server.send_status(
                    task_id=task_id,
                    status_info={
                        "status": status,
                        "phase": TaskPhase(phase),
                        "progress": progress,
                        "current_file": current_file,
                    }
                )
            except Exception as e:
                logger.error(f"Error sending extension update: {e}")
        
        # Update dashboard
        if self.dashboard_service:
            self.dashboard_service.update_task_progress(progress)
    
    async def record_file_edit(
        self,
        task_id: str,
        file_path: str,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
        operation: str = "modify",
    ) -> None:
        """
        Record file edit and notify extension.
        
        Args:
            task_id: Task identifier
            file_path: Path to file
            old_content: Original content (for diff)
            new_content: Modified content
            operation: "create", "modify", or "delete"
        """
        context = self.active_tasks.get(task_id)
        if not context:
            return
        
        # Calculate changes
        old_lines = len(old_content.split('\n')) if old_content else 0
        new_lines = len(new_content.split('\n')) if new_content else 0
        
        lines_added = max(0, new_lines - old_lines)
        lines_removed = max(0, old_lines - new_lines)
        
        context.record_file_edit(file_path, lines_added, lines_removed)
        
        # Notify extension
        if self.extension_server:
            try:
                await self.extension_server.send_file_edit(
                    task_id=task_id,
                    file_path=file_path,
                    operation=operation,
                    old_content=old_content,
                    new_content=new_content,
                    current_line=context.current_line,
                )
            except Exception as e:
                logger.error(f"Error sending file edit notification: {e}")
    
    async def request_approval(
        self,
        task_id: str,
        reason: str,
        files_affected: List[str],
    ) -> bool:
        """
        Request approval for changes.
        
        Args:
            task_id: Task identifier
            reason: Why approval is needed
            files_affected: List of affected files
        
        Returns:
            True if approved by user
        """
        logger.info(f"Requesting approval for task {task_id}: {reason}")
        
        # Notify extension
        if self.extension_server:
            try:
                await self.extension_server.send_approval_required(
                    task_id=task_id,
                    reason=reason,
                    files_affected=files_affected,
                )
            except Exception as e:
                logger.error(f"Error sending approval request: {e}")
        
        # In a real implementation, would wait for user response
        # For now, return True (auto-approve)
        return True
    
    async def record_error(self, task_id: str, error_msg: str) -> None:
        """Record error and notify dashboard."""
        context = self.active_tasks.get(task_id)
        if context:
            context.record_error(error_msg)
            
            if self.dashboard_service:
                self.dashboard_service.record_error_fixed(task_id, error_msg)
    
    async def record_test_result(
        self,
        task_id: str,
        test_name: str,
        passed: bool,
        duration: float = 0.0,
    ) -> None:
        """Record test result."""
        context = self.active_tasks.get(task_id)
        if context:
            context.record_test_result(passed)
            
            if self.dashboard_service:
                self.dashboard_service.add_metric(
                    name=f"test_{test_name}",
                    value=1.0 if passed else 0.0,
                    unit="pass/fail"
                )
    
    async def complete_task(self, task_id: str) -> TaskMetrics:
        """
        Complete task and extract metrics.
        
        Args:
            task_id: Task identifier
        
        Returns:
            TaskMetrics for the completed task
        """
        context = self.active_tasks.pop(task_id)
        self.completed_tasks.append(context)
        
        # Create metrics
        from code_alpha.dashboard import TaskMetrics
        
        metrics = TaskMetrics(
            task_id=task_id,
            status="completed",
            phase=context.phase,
            progress=100,
            duration_seconds=int(context.get_duration_seconds()),
            files_modified=context.files_modified,
            lines_added=context.lines_added,
            lines_removed=context.lines_removed,
            tests_run=context.tests_run,
            tests_passed=context.tests_passed,
            tests_failed=context.tests_failed,
            errors_encountered=context.errors_encountered,
            errors_fixed=context.errors_fixed,
        )
        
        # Update dashboard
        if self.dashboard_service:
            self.dashboard_service.record_task_completion(metrics)
        
        # Extract and store new conventions
        try:
            from code_alpha.memory import MemoryExtractor
            
            extractor = MemoryExtractor(self.memory_manager.get_memory())
            updated_count = extractor.extract_from_task_result(context.to_dict())
            
            self.memory_manager.save()
            logger.info(f"Extracted {updated_count} conventions from task {task_id}")
        except Exception as e:
            logger.warning(f"Error extracting conventions: {e}")
        
        logger.info(f"Task {task_id} completed with metrics: {metrics.to_dict()}")
        
        return metrics
    
    def get_task_context(self, task_id: str) -> Optional[TaskContext]:
        """Get context for active task."""
        return self.active_tasks.get(task_id)
    
    def get_memory_context(self, task_id: str) -> str:
        """Get memory context for task."""
        context = self.active_tasks.get(task_id)
        return context.memory_conventions if context else ""

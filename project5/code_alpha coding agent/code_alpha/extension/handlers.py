"""
Message handlers for VS Code extension communication.

Processes incoming control messages and coordinates responses.
"""

import logging
from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass

from .models import ControlCommand, FileEdit, DiffInfo, ExtensionMessage

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """Request for approval of changes."""
    
    task_id: str
    reason: str
    files_affected: List[str]
    pending_approval: bool = True


class TaskController:
    """
    Controls task execution in response to IDE commands.
    
    Maps control messages to agent actions.
    """
    
    def __init__(self):
        self.task_controllers: Dict[str, Callable] = {}
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
    
    async def pause_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Pause running task."""
        logger.info(f"Pausing task {task_id}: {reason}")
        handler = self.task_controllers.get('pause')
        if handler:
            try:
                if callable(handler):
                    result = handler(task_id)
                    # Support both sync and async
                    import asyncio
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
            except Exception as e:
                logger.error(f"Error pausing task: {e}")
        return False
    
    async def resume_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Resume paused task."""
        logger.info(f"Resuming task {task_id}: {reason}")
        handler = self.task_controllers.get('resume')
        if handler:
            try:
                if callable(handler):
                    result = handler(task_id)
                    import asyncio
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
            except Exception as e:
                logger.error(f"Error resuming task: {e}")
        return False
    
    async def stop_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Stop running task."""
        logger.info(f"Stopping task {task_id}: {reason}")
        handler = self.task_controllers.get('stop')
        if handler:
            try:
                if callable(handler):
                    result = handler(task_id)
                    import asyncio
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
            except Exception as e:
                logger.error(f"Error stopping task: {e}")
        return False
    
    async def approve_changes(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Approve pending changes."""
        logger.info(f"Approving changes for task {task_id}: {reason}")
        
        # Remove from pending
        if task_id in self.pending_approvals:
            del self.pending_approvals[task_id]
        
        handler = self.task_controllers.get('approve')
        if handler:
            try:
                if callable(handler):
                    result = handler(task_id)
                    import asyncio
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
            except Exception as e:
                logger.error(f"Error approving changes: {e}")
        return False
    
    async def reject_changes(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Reject pending changes."""
        logger.info(f"Rejecting changes for task {task_id}: {reason}")
        
        # Remove from pending
        if task_id in self.pending_approvals:
            del self.pending_approvals[task_id]
        
        handler = self.task_controllers.get('reject')
        if handler:
            try:
                if callable(handler):
                    result = handler(task_id)
                    import asyncio
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
            except Exception as e:
                logger.error(f"Error rejecting changes: {e}")
        return False
    
    async def request_changes(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Request changes to pending approval."""
        logger.info(f"Requesting changes for task {task_id}: {reason}")
        
        handler = self.task_controllers.get('request_changes')
        if handler:
            try:
                if callable(handler):
                    result = handler(task_id, reason)
                    import asyncio
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
            except Exception as e:
                logger.error(f"Error requesting changes: {e}")
        return False
    
    def register_controller(self, command: str, handler: Callable) -> None:
        """Register handler for command."""
        self.task_controllers[command] = handler
        logger.debug(f"Registered controller for: {command}")
    
    def request_approval(
        self,
        task_id: str,
        reason: str,
        files_affected: List[str]
    ) -> None:
        """Record approval request."""
        self.pending_approvals[task_id] = ApprovalRequest(
            task_id=task_id,
            reason=reason,
            files_affected=files_affected,
        )
        logger.info(f"Approval requested for task {task_id}")
    
    def get_pending_approval(self, task_id: str) -> Optional[ApprovalRequest]:
        """Get pending approval request."""
        return self.pending_approvals.get(task_id)


class DiffHandler:
    """
    Handles diff preview and review operations.
    
    Prepares diffs for display in VS Code diff viewer.
    """
    
    @staticmethod
    def create_diff(
        file_path: str,
        old_content: str,
        new_content: str,
        language: str = "python"
    ) -> DiffInfo:
        """
        Create diff information for file changes.
        
        Args:
            file_path: Path to file
            old_content: Original content
            new_content: Modified content
            language: File language for syntax highlighting
        
        Returns:
            DiffInfo object
        """
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        return DiffInfo(
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
            old_range=(0, len(old_lines)),
            new_range=(0, len(new_lines)),
            language=language,
        )
    
    @staticmethod
    def prepare_diffs_for_review(
        changes: List[Dict[str, Any]]
    ) -> List[DiffInfo]:
        """
        Prepare multiple file changes for review.
        
        Args:
            changes: List of change dicts with old/new content
        
        Returns:
            List of DiffInfo objects
        """
        diffs = []
        for change in changes:
            diff = DiffHandler.create_diff(
                file_path=change['file_path'],
                old_content=change.get('old_content', ''),
                new_content=change['new_content'],
                language=change.get('language', 'python'),
            )
            diffs.append(diff)
        
        return diffs


class MessageHandler:
    """
    High-level message handler orchestrating all message types.
    
    Routes messages to appropriate handlers.
    """
    
    def __init__(self):
        self.task_controller = TaskController()
        self.diff_handler = DiffHandler()
        self.message_handlers: Dict[str, Callable] = {}
    
    async def handle_control_command(
        self,
        command: ControlCommand,
        task_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Handle control command from IDE.
        
        Args:
            command: ControlCommand (pause, resume, stop, etc.)
            task_id: Task to control
            reason: Optional reason for action
        
        Returns:
            Success status
        """
        logger.info(f"Handling control command: {command.value} for task: {task_id}")
        
        # Dispatch to appropriate method
        if command == ControlCommand.PAUSE:
            return await self.task_controller.pause_task(task_id, reason)
        elif command == ControlCommand.RESUME:
            return await self.task_controller.resume_task(task_id, reason)
        elif command == ControlCommand.STOP:
            return await self.task_controller.stop_task(task_id, reason)
        elif command == ControlCommand.APPROVE:
            return await self.task_controller.approve_changes(task_id, reason)
        elif command == ControlCommand.REJECT:
            return await self.task_controller.reject_changes(task_id, reason)
        elif command == ControlCommand.REQUEST_CHANGES:
            return await self.task_controller.request_changes(task_id, reason)
        else:
            logger.warning(f"Unknown command: {command}")
            return False
    
    def register_message_handler(
        self,
        message_type: str,
        handler: Callable
    ) -> None:
        """
        Register handler for message type.
        
        Args:
            message_type: Message type to handle
            handler: Async callable to process message
        """
        self.message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    async def process_message(
        self,
        message_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Process incoming message.
        
        Args:
            message_type: Type of message
            data: Message data
        
        Returns:
            Success status
        """
        handler = self.message_handlers.get(message_type)
        if handler:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    return await handler(data)
                else:
                    return handler(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                return False
        
        logger.debug(f"No handler for message type: {message_type}")
        return False

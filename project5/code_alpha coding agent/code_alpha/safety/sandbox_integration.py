"""
Sandbox Integration for Code Alpha Safety

Enforces safety policies at the sandbox level (tool execution).
"""

from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """Types of tools/operations."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL_COMMAND = "shell_command"
    API_CALL = "api_call"
    DATABASE_QUERY = "database_query"
    GIT_OPERATION = "git_operation"


@dataclass
class ToolCall:
    """Information about a tool call."""
    
    tool_type: ToolType
    arguments: Dict[str, Any]
    task_id: str
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'tool_type': self.tool_type.value,
            'arguments': self.arguments,
            'task_id': self.task_id,
            'user_id': self.user_id,
        }


@dataclass
class ToolCallResult:
    """Result of a tool call."""
    
    tool_type: ToolType
    allowed: bool
    reason: Optional[str] = None
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'tool_type': self.tool_type.value,
            'allowed': self.allowed,
            'reason': self.reason,
            'requires_approval': self.requires_approval,
            'approval_request_id': self.approval_request_id,
            'details': self.details or {},
        }


class PreToolValidator:
    """Validates tool calls before execution."""
    
    def __init__(self):
        """Initialize validator."""
        self.validators: Dict[ToolType, Callable[[ToolCall], ToolCallResult]] = {}
    
    def register(
        self,
        tool_type: ToolType,
        validator: Callable[[ToolCall], ToolCallResult],
    ) -> None:
        """Register a validator for a tool type."""
        self.validators[tool_type] = validator
        logger.info(f"Registered validator for {tool_type.value}")
    
    def validate(self, tool_call: ToolCall) -> ToolCallResult:
        """Validate a tool call."""
        validator = self.validators.get(tool_call.tool_type)
        
        if not validator:
            # No validator registered, allow by default
            return ToolCallResult(
                tool_type=tool_call.tool_type,
                allowed=True,
                reason="No validator registered",
            )
        
        try:
            return validator(tool_call)
        except Exception as e:
            logger.error(f"Error in tool validator: {e}")
            return ToolCallResult(
                tool_type=tool_call.tool_type,
                allowed=False,
                reason=f"Validator error: {str(e)}",
            )


class PostToolLogger:
    """Logs tool calls after execution."""
    
    def __init__(self):
        """Initialize logger."""
        self.loggers: Dict[ToolType, Callable[[ToolCall, Any], None]] = {}
    
    def register(
        self,
        tool_type: ToolType,
        logger_func: Callable[[ToolCall, Any], None],
    ) -> None:
        """Register a logger for a tool type."""
        self.loggers[tool_type] = logger_func
        logger.info(f"Registered logger for {tool_type.value}")
    
    def log_execution(self, tool_call: ToolCall, result: Any) -> None:
        """Log a tool execution."""
        logger_func = self.loggers.get(tool_call.tool_type)
        
        if not logger_func:
            return
        
        try:
            logger_func(tool_call, result)
        except Exception as e:
            logger.error(f"Error in post-tool logger: {e}")


class SandboxIntegration:
    """
    Integrates safety policies into sandbox tool execution.
    
    Provides:
    - Pre-tool validation hooks
    - Post-tool logging hooks
    - Tool blocking enforcement
    - Emergency stop capability
    """
    
    def __init__(self):
        """Initialize sandbox integration."""
        self.pre_validator = PreToolValidator()
        self.post_logger = PostToolLogger()
        self.emergency_stop_enabled = False
        self.blocked_tools: List[ToolType] = []
        
        logger.info("SandboxIntegration initialized")
    
    def register_pre_validator(
        self,
        tool_type: ToolType,
        validator: Callable[[ToolCall], ToolCallResult],
    ) -> None:
        """Register a pre-execution validator."""
        self.pre_validator.register(tool_type, validator)
    
    def register_post_logger(
        self,
        tool_type: ToolType,
        logger_func: Callable[[ToolCall, Any], None],
    ) -> None:
        """Register a post-execution logger."""
        self.post_logger.register(tool_type, logger_func)
    
    def validate_tool_call(self, tool_call: ToolCall) -> ToolCallResult:
        """
        Validate a tool call before execution.
        
        Checks:
        1. Emergency stop
        2. Blocked tools list
        3. Pre-validators
        """
        # Check emergency stop
        if self.emergency_stop_enabled:
            logger.critical(f"Tool call blocked: emergency stop active")
            return ToolCallResult(
                tool_type=tool_call.tool_type,
                allowed=False,
                reason="Emergency stop is active",
            )
        
        # Check blocked tools
        if tool_call.tool_type in self.blocked_tools:
            logger.warning(
                f"Tool call blocked: {tool_call.tool_type.value} is blocked"
            )
            return ToolCallResult(
                tool_type=tool_call.tool_type,
                allowed=False,
                reason=f"Tool {tool_call.tool_type.value} is blocked",
            )
        
        # Run pre-validators
        return self.pre_validator.validate(tool_call)
    
    def log_tool_execution(self, tool_call: ToolCall, result: Any) -> None:
        """Log a tool execution."""
        self.post_logger.log_execution(tool_call, result)
    
    def block_tool(self, tool_type: ToolType) -> None:
        """Block a tool type."""
        if tool_type not in self.blocked_tools:
            self.blocked_tools.append(tool_type)
            logger.warning(f"Blocked tool: {tool_type.value}")
    
    def unblock_tool(self, tool_type: ToolType) -> None:
        """Unblock a tool type."""
        if tool_type in self.blocked_tools:
            self.blocked_tools.remove(tool_type)
            logger.info(f"Unblocked tool: {tool_type.value}")
    
    def enable_emergency_stop(self) -> None:
        """Enable emergency stop."""
        self.emergency_stop_enabled = True
        logger.critical("Emergency stop ENABLED - all tool calls will be blocked")
    
    def disable_emergency_stop(self) -> None:
        """Disable emergency stop."""
        self.emergency_stop_enabled = False
        logger.info("Emergency stop disabled")
    
    def is_emergency_stop_active(self) -> bool:
        """Check if emergency stop is active."""
        return self.emergency_stop_enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get current sandbox integration status."""
        return {
            'emergency_stop_enabled': self.emergency_stop_enabled,
            'blocked_tools': [t.value for t in self.blocked_tools],
            'num_blocked_tools': len(self.blocked_tools),
            'pre_validators_registered': len(self.pre_validator.validators),
            'post_loggers_registered': len(self.post_logger.loggers),
        }


# Global singleton instance
_sandbox_integration: Optional[SandboxIntegration] = None


def get_sandbox_integration() -> SandboxIntegration:
    """Get or create the global sandbox integration instance."""
    global _sandbox_integration
    
    if _sandbox_integration is None:
        _sandbox_integration = SandboxIntegration()
    
    return _sandbox_integration


def reset_sandbox_integration() -> None:
    """Reset the sandbox integration (for testing)."""
    global _sandbox_integration
    _sandbox_integration = None

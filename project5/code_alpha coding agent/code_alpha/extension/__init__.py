"""
VS Code Extension Interface for Code Alpha

Provides WebSocket-based real-time agent status, task control, and diff viewing.
Enables bidirectional communication between VS Code extension and Code Alpha agent.
"""

from .models import (
    ExtensionMessage,
    AgentStatus,
    TaskUpdate,
    FileEdit,
    DiffInfo,
    ControlMessage,
    MessageType,
    TaskPhase,
    ControlCommand,
)
from .server import ExtensionServer, ConnectionManager
from .handlers import MessageHandler, TaskController, DiffHandler

__all__ = [
    'ExtensionMessage',
    'AgentStatus',
    'TaskUpdate',
    'FileEdit',
    'DiffInfo',
    'ControlMessage',
    'MessageType',
    'TaskPhase',
    'ControlCommand',
    'ExtensionServer',
    'ConnectionManager',
    'MessageHandler',
    'TaskController',
    'DiffHandler',
]

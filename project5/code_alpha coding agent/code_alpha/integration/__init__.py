"""
Agent Context Integration Module

Integrates memory system, extension interface, and dashboard into orchestrator.
Provides convention-aware code generation and real-time status updates.
"""

from .context_manager import ContextManager, TaskContext
from .orchestrator_adapter import OrchestratorAdapter
from .prompt_enhancer import PromptEnhancer

__all__ = [
    'ContextManager',
    'TaskContext',
    'OrchestratorAdapter',
    'PromptEnhancer',
]

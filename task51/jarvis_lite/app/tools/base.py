"""
Base Tool interface and abstract class for all tools.

Tools are reusable components that the agent can invoke to solve problems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolInput:
    """Structured input to a tool."""
    tool_name: str
    parameters: Dict[str, Any]


@dataclass
class ToolOutput:
    """Structured output from a tool."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata or {},
        }


class BaseTool(ABC):
    """Abstract base class for all tools."""

    def __init__(self, name: str, description: str) -> None:
        """
        Initialize tool.
        
        Args:
            name: Tool name (used by agent for routing)
            description: Tool description (used by agent for understanding)
        """
        self.name = name
        self.description = description

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Return tool schema for agent understanding.
        
        Should describe what parameters this tool accepts.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, **kwargs) -> ToolOutput:
        """
        Execute the tool with given parameters.
        
        Returns:
            ToolOutput with success/error status and result
        """
        raise NotImplementedError

    def __call__(self, **kwargs) -> ToolOutput:
        """Allow tool to be called directly."""
        return self.execute(**kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"

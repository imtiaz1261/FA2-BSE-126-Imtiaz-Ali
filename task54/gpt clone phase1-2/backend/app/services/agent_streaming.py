"""
Streaming response system for agent reasoning.

Converts agent events to SSE-compatible format for frontend consumption.
"""

import json
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


# ============================================================================
# SSE Event Formatter
# ============================================================================


class SSEFormatter:
    """Format events as Server-Sent Events."""

    @staticmethod
    def format_event(event_type: str, data: dict) -> str:
        """
        Format event as SSE.

        Args:
            event_type: Event type identifier
            data: Event data dictionary

        Returns:
            SSE-formatted string
        """
        event_data = json.dumps({"type": event_type, **data})
        return f"data: {event_data}\n\n"

    @staticmethod
    async def stream_agent_events(
        agent_generator: AsyncGenerator,
    ) -> AsyncGenerator[str, None]:
        """
        Convert agent events to SSE stream.

        Args:
            agent_generator: Agent event generator

        Yields:
            SSE-formatted event strings
        """
        try:
            async for event in agent_generator:
                yield SSEFormatter.format_event(
                    event.get("type", "unknown"),
                    event,
                )
        except Exception as e:
            logger.error(f"Stream error: {e}")
            error_event = {
                "type": "error",
                "message": str(e),
            }
            yield SSEFormatter.format_event("error", error_event)


# ============================================================================
# Agent Event Stream
# ============================================================================


class AgentEventStream:
    """Manages agent event streaming to multiple clients."""

    def __init__(self, session_id: str):
        """Initialize event stream."""
        self.session_id = session_id
        self.events = []
        self.complete = False

    def add_event(self, event: dict) -> None:
        """Add event to stream."""
        self.events.append(event)

    async def stream(self) -> AsyncGenerator[str, None]:
        """
        Stream all events as SSE.

        Yields:
            SSE-formatted events
        """
        for event in self.events:
            yield SSEFormatter.format_event(event.get("type", "unknown"), event)

        if self.complete:
            yield SSEFormatter.format_event("stream_end", {"session_id": self.session_id})


# ============================================================================
# Event Types
# ============================================================================


class AgentEvents:
    """Standard agent event types and formatters."""

    @staticmethod
    def phase_change(phase: str) -> dict:
        """Phase change event."""
        return {
            "type": "phase_change",
            "phase": phase,
        }

    @staticmethod
    def reasoning(step_type: str, content: str) -> dict:
        """Reasoning step event."""
        return {
            "type": "reasoning",
            "step": step_type,
            "content": content,
        }

    @staticmethod
    def tool_call(tool_name: str, tool_input: dict) -> dict:
        """Tool call event."""
        return {
            "type": "tool_call",
            "tool": tool_name,
            "input": tool_input,
        }

    @staticmethod
    def tool_result(tool_name: str, success: bool, output: str, error: str = None) -> dict:
        """Tool result event."""
        return {
            "type": "tool_result",
            "tool": tool_name,
            "success": success,
            "output": output,
            "error": error,
        }

    @staticmethod
    def change_proposed(file: str, operation: str, diff: str) -> dict:
        """Proposed change event."""
        return {
            "type": "change_proposed",
            "file": file,
            "operation": operation,
            "diff": diff,
        }

    @staticmethod
    def awaiting_approval(changes_count: int) -> dict:
        """Awaiting user approval event."""
        return {
            "type": "awaiting_approval",
            "changes_count": changes_count,
        }

    @staticmethod
    def test_result(passed: bool, output: str) -> dict:
        """Test result event."""
        return {
            "type": "test_result",
            "passed": passed,
            "output": output,
        }

    @staticmethod
    def complete(summary: str = None) -> dict:
        """Completion event."""
        return {
            "type": "complete",
            "summary": summary or "Task completed successfully",
        }

    @staticmethod
    def error(message: str, details: str = None) -> dict:
        """Error event."""
        return {
            "type": "error",
            "message": message,
            "details": details,
        }

    @staticmethod
    def iteration(iteration: int) -> dict:
        """Iteration event."""
        return {
            "type": "iteration",
            "iteration": iteration,
        }

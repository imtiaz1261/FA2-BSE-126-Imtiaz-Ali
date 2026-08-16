"""
errors.py
---------
Custom exceptions for the function-calling pipeline, so each failure
mode can be caught and handled distinctly (and logged with the right
severity/context) rather than collapsing everything into a generic
Exception.
"""


class ToolNotFoundError(Exception):
    """Raised when the LLM requests a tool name that isn't registered."""


class InvalidArgumentsError(Exception):
    """Raised when the LLM's tool call arguments fail schema validation."""


class ToolExecutionError(Exception):
    """Raised when a registered tool's Python function raises during execution
    (e.g. an upstream API failure, network error, or bad input it couldn't
    validate against the schema alone -- like an unknown stock ticker)."""

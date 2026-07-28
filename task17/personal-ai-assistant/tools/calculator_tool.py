"""
tools/calculator_tool.py
-------------------------
Calculator tool for mathematical operations.

Deliberately does NOT use Python's eval() on arbitrary user text (that
would let a malicious prompt execute arbitrary code). Instead it parses
the expression into an AST and only allows a safe whitelist of numeric
operators.
"""

import ast
import operator
from langchain_core.tools import tool

from utils import get_logger

logger = get_logger(__name__)

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class CalculatorError(Exception):
    """Raised for invalid or unsafe expressions."""


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalculatorError("Only numeric constants are allowed.")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise CalculatorError(f"Operator '{op_type.__name__}' is not allowed.")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _ALLOWED_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise CalculatorError(f"Operator '{op_type.__name__}' is not allowed.")
        return _ALLOWED_OPERATORS[op_type](_eval_node(node.operand))

    raise CalculatorError(f"Unsupported expression element: {type(node).__name__}")


def safe_calculate(expression: str) -> float:
    """Safely evaluate a numeric expression like '125 * 48' or '(3+4)/2'."""
    try:
        tree = ast.parse(expression, mode="eval")
        return _eval_node(tree.body)
    except ZeroDivisionError:
        raise CalculatorError("Division by zero.")
    except CalculatorError:
        raise
    except Exception as exc:
        raise CalculatorError(f"Could not parse expression '{expression}': {exc}")


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the numeric result.
    Use this for arithmetic like "125 * 48", "(200 - 35) / 3", "2**10".
    Only basic arithmetic operators are supported: + - * / // % **
    """
    logger.info("Calculator tool invoked with expression: %r", expression)
    try:
        result = safe_calculate(expression)
        return f"{expression} = {result}"
    except CalculatorError as exc:
        logger.warning("Calculator error: %s", exc)
        return f"Error: {exc}"

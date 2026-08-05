"""
Calculator tool — Phase 12.

Safely evaluates mathematical expressions using Python's AST so that
arbitrary code execution is impossible.  Supports:
  - Basic arithmetic: + - * / // % **
  - Parentheses and operator precedence
  - Unary minus/plus
  - Integer and float literals

Any expression that contains non-numeric, non-operator tokens is
rejected with a clear error message.
"""

import ast
import math
import operator as op
from typing import Any

# Allowed binary operators
_BIN_OPS: dict[type, Any] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

# Allowed unary operators
_UNARY_OPS: dict[type, Any] = {
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

# Allowed math functions (single-arg)
_MATH_FNS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,  # constant — accessed as Name node
    "e": math.e,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _MATH_FNS:
        val = _MATH_FNS[node.id]
        if callable(val):
            raise ValueError(f"'{node.id}' is a function, not a constant.")
        return float(val)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval(node.left)
        right = _eval(node.right)
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call):
        fn_name = node.func.id if isinstance(node.func, ast.Name) else None
        if fn_name and fn_name in _MATH_FNS and callable(_MATH_FNS[fn_name]):
            args = [_eval(a) for a in node.args]
            return _MATH_FNS[fn_name](*args)
    raise ValueError(f"Unsupported expression node: {ast.dump(node)}")


def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the result as a string.

    Args:
        expression: A math expression string, e.g. "2 + 2", "sqrt(144)", "3**10"

    Returns:
        The numeric result as a string, or an error message.
    """
    expression = expression.strip()
    if not expression:
        return "Error: empty expression."
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree)
        # Return integer representation when the result is whole
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(round(result, 10))
    except ZeroDivisionError:
        return "Error: division by zero."
    except (ValueError, TypeError, AttributeError) as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error evaluating expression: {exc}"

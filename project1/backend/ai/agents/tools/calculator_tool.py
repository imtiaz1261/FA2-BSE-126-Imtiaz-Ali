"""Calculator tool — safe math eval using AST (no eval())."""
from __future__ import annotations
import ast, math, operator
from backend.core.logging import get_logger

logger = get_logger(__name__)

_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.UAdd: operator.pos, ast.USub: operator.neg,
    ast.FloorDiv: operator.floordiv,
}
_SAFE_FUNCS = {
    "abs": abs, "round": round, "sqrt": math.sqrt,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "pi": math.pi,
    "e": math.e, "ceil": math.ceil, "floor": math.floor,
    "pow": math.pow, "factorial": math.factorial,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _SAFE_OPS.get(type(node.op))
        if not op:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _SAFE_OPS.get(type(node.op))
        if not op:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCS:
            args = [_safe_eval(a) for a in node.args]
            return _SAFE_FUNCS[node.func.id](*args)
        raise ValueError(f"Function '{node.func.id if isinstance(node.func, ast.Name) else '?'}' is not allowed")
    if isinstance(node, ast.Name) and node.id in _SAFE_FUNCS:
        return _SAFE_FUNCS[node.id]
    raise ValueError(f"Unsupported expression: {type(node).__name__}")


def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.
    Supports: +, -, *, /, **, %, //, abs, round, sqrt, sin, cos, tan, log, pi, e.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree.body)
        logger.info("calculator_used", expression=expression, result=result)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as exc:
        return f"Error evaluating expression: {exc}"

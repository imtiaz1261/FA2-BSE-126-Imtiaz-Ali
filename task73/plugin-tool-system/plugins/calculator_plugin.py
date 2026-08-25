"""
plugins/calculator_plugin.py
-------------------------------
Sample plugin: safe arithmetic evaluation (AST-based, no eval()).
"""

import ast
import operator

from core.base_plugin import BasePlugin, PluginExecutionError

_ALLOWED_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_eval_node(node.operand))
    raise PluginExecutionError("Unsupported or unsafe expression.")


class CalculatorPlugin(BasePlugin):
    name = "calculator"
    description = "Evaluate a mathematical expression, e.g. '125 * 48' or '(200-35)/3'."
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "The math expression to evaluate."},
        },
        "required": ["expression"],
    }

    def execute(self, expression: str) -> str:
        try:
            tree = ast.parse(expression, mode="eval")
            result = _eval_node(tree.body)
        except ZeroDivisionError:
            raise PluginExecutionError("Division by zero.")
        except PluginExecutionError:
            raise
        except Exception as exc:
            raise PluginExecutionError(f"Could not evaluate '{expression}': {exc}")
        return f"{expression} = {result}"

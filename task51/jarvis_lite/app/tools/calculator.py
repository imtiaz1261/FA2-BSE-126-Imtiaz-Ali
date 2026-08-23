"""
Calculator Tool — performs mathematical operations.

Handles arithmetic, trigonometry, and other common math operations.
"""

import logging
import math
from typing import Any, Dict, Union

from app.core.exceptions import ToolError
from app.tools.base import BaseTool, ToolOutput

logger = logging.getLogger(__name__)


class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations."""

    def __init__(self) -> None:
        super().__init__(
            name="calculator",
            description="Performs mathematical calculations. "
                       "Supports arithmetic (+, -, *, /), power (**), "
                       "trigonometry (sin, cos, tan), and more. "
                       "Example: 'calculate: 2 + 2' or 'calculate: sqrt(16)'"
        )
        self._safe_functions = {
            'abs': abs,
            'round': round,
            'max': max,
            'min': min,
            'sum': sum,
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e,
        }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate. "
                                  "Can include: +, -, *, /, **, sqrt(), sin(), cos(), tan(), log(), etc."
                }
            },
            "required": ["expression"]
        }

    def execute(self, expression: str, **kwargs) -> ToolOutput:
        """
        Evaluate mathematical expression safely.
        
        Args:
            expression: Math expression to evaluate
            
        Returns:
            ToolOutput with calculation result
        """
        try:
            if not isinstance(expression, str):
                raise ToolError(f"Expression must be a string, got {type(expression)}")
            
            # Clean up the expression
            expression = expression.strip()
            
            # Validate: only allow safe characters
            allowed_chars = set("0123456789+-*/.()^ ")
            allowed_chars.update("abcdefghijklmnopqrstuvwxyz")
            allowed_chars.update("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            allowed_chars.add("_")
            
            for char in expression:
                if char not in allowed_chars:
                    raise ToolError(f"Invalid character in expression: {char}")
            
            # Check for consecutive operators (malformed expressions)
            import re
            # Remove spaces to detect consecutive operators
            expr_no_spaces = expression.replace(' ', '')
            if re.search(r'[+\-*/]{2,}', expr_no_spaces.replace('**', '')):
                raise ToolError(f"Invalid expression: consecutive operators detected")
            
            # Replace ^ with ** for power
            expression = expression.replace("^", "**")
            
            # Evaluate with safe namespace
            result = eval(expression, {"__builtins__": {}}, self._safe_functions)
            
            # Handle different result types
            if isinstance(result, (int, float)):
                result = round(result, 10)  # Round to 10 decimals
            
            logger.info(f"Calculator: {expression} = {result}")
            
            return ToolOutput(
                tool_name=self.name,
                success=True,
                result=result,
                metadata={"expression": expression}
            )
        
        except ToolError as e:
            logger.warning(f"Calculator error: {e}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=str(e),
                metadata={"expression": expression}
            )
        except ZeroDivisionError:
            error = "Division by zero"
            logger.warning(f"Calculator: {error}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=error,
                metadata={"expression": expression}
            )
        except ValueError as e:
            error = f"Math error: {e}"
            logger.warning(f"Calculator: {error}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=error,
                metadata={"expression": expression}
            )
        except Exception as e:
            error = f"Calculation failed: {e}"
            logger.exception(f"Calculator exception: {e}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=error,
                metadata={"expression": expression}
            )

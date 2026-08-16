"""
tools package
-------------
Central tool registry. To add a new tool later:
  1. Create tools/my_new_tool.py exporting a SCHEMA dict (OpenAI/Groq
     function-calling format) and the executable Python function.
  2. Import both below and add them to TOOL_SCHEMAS / TOOL_REGISTRY.
That's the entire integration surface -- engine.py never needs to change.
"""

from tools.weather_tool import SCHEMA as WEATHER_SCHEMA, get_weather
from tools.stock_tool import SCHEMA as STOCK_SCHEMA, get_stock_price

# Sent to the LLM so it knows what tools exist and how to call them.
TOOL_SCHEMAS = [
    WEATHER_SCHEMA,
    STOCK_SCHEMA,
]

# Used by the engine to actually execute a tool once the LLM selects it.
TOOL_REGISTRY = {
    "get_weather": get_weather,
    "get_stock_price": get_stock_price,
}

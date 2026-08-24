"""Tool schemas the Coder/Planner/Fixer agents can call against a ContextEngine,
in Anthropic tool-use format. Wire these into the `tools=[...]` param of the
Messages API calls made by agents in code_alpha/agents/."""

TOOL_DEFINITIONS = [
    {
        "name": "search_code",
        "description": "Semantic search over the indexed repository. Returns the "
                        "most relevant functions/classes/files for a natural-language "
                        "or code-like query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for"},
                "top_k": {"type": "integer", "description": "Max results", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "find_usages",
        "description": "Find every definition and call site of a symbol (function "
                        "or class name) across the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol name to look up"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_file",
        "description": "Return the full source of a file, given a path relative to "
                        "the repo root (or absolute).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_dependency_graph",
        "description": "Return the repo's file-level import graph: which files "
                        "import which. Takes no arguments.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def dispatch(engine, tool_name: str, tool_input: dict):
    """Route a tool_use block from the model to the matching ContextEngine method."""
    handlers = {
        "search_code": lambda: engine.search_code(**tool_input),
        "find_usages": lambda: engine.find_usages(**tool_input),
        "get_file": lambda: engine.get_file(**tool_input),
        "get_dependency_graph": lambda: engine.get_dependency_graph(),
    }
    if tool_name not in handlers:
        raise ValueError(f"unknown tool: {tool_name}")
    return handlers[tool_name]()

"""
core/base_plugin.py
---------------------
The standard tool interface every plugin must implement. This is the
entire contract between a plugin and the system -- as long as a
plugin subclasses BasePlugin and fills in these four things, the
registry can discover it, the agent can call it, and the admin UI can
list it, with ZERO changes to any core file.
"""

from abc import ABC, abstractmethod


class PluginExecutionError(Exception):
    """A plugin should raise this for any expected failure during
    execute() (bad input it couldn't validate via schema alone, an
    upstream API failure, etc.) so the agent can handle it gracefully."""


class BasePlugin(ABC):
    """
    Subclass this to create a new tool. Required class attributes:

    name : str
        Unique tool name (used as the function-calling schema name).
    description : str
        Shown to the LLM so it knows when to use this tool.
    input_schema : dict
        JSON Schema for the tool's parameters (OpenAI/Groq
        function-calling "parameters" format) -- type, properties,
        required fields.

    Required method:

    execute(self, **kwargs) -> str
        Run the tool with validated arguments and return a result
        (plain text or a JSON-serializable string). Raise
        PluginExecutionError for any expected failure.
    """

    name: str = ""
    description: str = ""
    input_schema: dict = {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        raise NotImplementedError

"""
core/agent.py
---------------
The agent that talks to Groq and calls plugins -- entirely driven by
PluginRegistry. This file never imports or references any specific
plugin by name; it only ever asks the registry "what's enabled right
now?" and "run this one for me." That's what makes adding/removing
tools not require touching this file.
"""

import json

from config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE, MAX_TOOL_CALL_ROUNDS
from core.base_plugin import PluginExecutionError
from core.registry import PluginRegistry, PluginNotFoundError, InvalidPluginArgumentsError
from utils import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a dynamic set of tools "
    "(plugins). The available tools can change at any time -- always use "
    "exactly the tools currently offered to you, and only when the user's "
    "request actually needs one. For anything else, answer directly."
)


class AgentInitError(Exception):
    """Raised when the agent can't be built (e.g. missing API key)."""


class AgentRequestError(Exception):
    """Raised when the configured LLM cannot complete a request."""


class PluginAgent:
    def __init__(self, registry: PluginRegistry = None):
        if not GROQ_API_KEY:
            raise AgentInitError(
                "GROQ_API_KEY is missing from your .env file. Get a free key "
                "at https://console.groq.com/keys and add it as "
                "GROQ_API_KEY=... in your local .env file."
            )
        try:
            from groq import Groq
        except ImportError as exc:
            raise AgentInitError("The groq package is not installed. Run: pip install groq") from exc

        self.client = Groq(api_key=GROQ_API_KEY)
        self.registry = registry or PluginRegistry()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _execute_plugin(self, name: str, arguments: dict) -> dict:
        logger.info("Plugin selected: %s | arguments: %s", name, arguments)
        try:
            result = self.registry.execute(name, arguments)
            logger.info("Plugin '%s' executed successfully.", name)
            return {"result": result}
        except PluginNotFoundError as exc:
            logger.warning(str(exc))
            return {"error": str(exc)}
        except InvalidPluginArgumentsError as exc:
            logger.warning(str(exc))
            return {"error": str(exc)}
        except PluginExecutionError as exc:
            logger.error("Plugin '%s' execution failed: %s", name, exc)
            return {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001 -- safety net
            logger.error("Unexpected error running plugin '%s': %s", name, exc)
            return {"error": f"Unexpected error running '{name}': {exc}"}

    def ask(self, user_query: str) -> str:
        """One full turn, re-fetching the CURRENT tool schemas from the
        registry every time -- so a plugin enabled/added moments ago is
        available on this very call, with no restart needed."""
        self.messages.append({"role": "user", "content": user_query})

        for _ in range(MAX_TOOL_CALL_ROUNDS):
            tool_schemas = self.registry.get_tool_schemas()  # always fresh

            try:
                response = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    temperature=LLM_TEMPERATURE,
                    messages=self.messages,
                    tools=tool_schemas if tool_schemas else None,
                    tool_choice="auto" if tool_schemas else None,
                )
            except Exception as exc:  # Provider errors should not break the Streamlit UI.
                logger.exception("Groq request failed using model '%s'.", GROQ_MODEL)
                # Remove the pending user message, so the next request starts cleanly.
                if self.messages and self.messages[-1].get("role") == "user":
                    self.messages.pop()
                raise AgentRequestError(
                    f"Groq could not run the configured model '{GROQ_MODEL}'. "
                    "Check GROQ_MODEL in .env and restart Streamlit. "
                    f"Provider details: {exc}"
                ) from exc
            message = response.choices[0].message

            if not message.tool_calls:
                final_text = (message.content or "").strip()
                self.messages.append({"role": "assistant", "content": final_text})
                return final_text

            self.messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            })

            for tool_call in message.tool_calls:
                name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}

                result = self._execute_plugin(name, arguments)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        fallback = "I wasn't able to finish that request after multiple tool calls. Please try rephrasing."
        self.messages.append({"role": "assistant", "content": fallback})
        return fallback

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

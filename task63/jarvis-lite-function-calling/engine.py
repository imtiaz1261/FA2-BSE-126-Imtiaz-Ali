"""
engine.py
---------
The core function-calling engine, implementing the exact flow:

    User Query -> LLM -> Determine Tool Required -> Function Calling
    Schema -> Execute Python Function -> Tool Result -> LLM -> Final Response

Uses the Groq SDK directly (OpenAI-compatible chat completions API
with `tools=`), so the tool-selection and schema-validation logic is
fully explicit and inspectable -- nothing is hidden behind a
higher-level agent framework.
"""

import json

import jsonschema

from config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE, MAX_TOOL_CALL_ROUNDS
from errors import ToolNotFoundError, InvalidArgumentsError, ToolExecutionError
from tools import TOOL_SCHEMAS, TOOL_REGISTRY
from utils import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are Jarvis-Lite, a helpful AI knowledge assistant. You have access "
    "to tools for checking live weather and stock prices. Use a tool ONLY "
    "when the user's question actually requires that live data -- for "
    "general knowledge, conversation, or anything else, answer directly "
    "without calling a tool. When you use a tool, base your final answer "
    "only on the data it returns."
)


class EngineInitError(Exception):
    """Raised when the engine can't be built (e.g. missing API key)."""


def _schema_for(tool_name: str) -> dict:
    for schema in TOOL_SCHEMAS:
        if schema["function"]["name"] == tool_name:
            return schema["function"]["parameters"]
    return {}


def _validate_arguments(tool_name: str, arguments: dict) -> None:
    """Validate tool call arguments against that tool's JSON schema.
    Raises InvalidArgumentsError with a clear message on failure."""
    schema = _schema_for(tool_name)
    try:
        jsonschema.validate(instance=arguments, schema=schema)
    except jsonschema.ValidationError as exc:
        raise InvalidArgumentsError(
            f"Invalid arguments for '{tool_name}': {exc.message}"
        ) from exc


def _execute_tool(tool_name: str, arguments: dict) -> dict:
    """
    Run the full per-call pipeline: lookup -> validate -> execute -> log.
    Never raises -- always returns a dict, either the tool's real result
    or a structured {"error": "..."} so the LLM can still respond
    sensibly instead of the whole request crashing.
    """
    logger.info("Tool selected: %s | arguments: %s", tool_name, arguments)

    try:
        if tool_name not in TOOL_REGISTRY:
            raise ToolNotFoundError(f"Tool '{tool_name}' is not available.")
        _validate_arguments(tool_name, arguments)
    except ToolNotFoundError as exc:
        logger.warning("Tool not found: %s", exc)
        return {"error": str(exc)}
    except InvalidArgumentsError as exc:
        logger.warning("Argument validation failed for %s: %s", tool_name, exc)
        return {"error": str(exc)}

    try:
        result = TOOL_REGISTRY[tool_name](**arguments)
        logger.info("Tool '%s' executed successfully | result: %s", tool_name, result)
        return result
    except ToolExecutionError as exc:
        logger.error("Tool '%s' execution failed: %s", tool_name, exc)
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001 -- deliberate catch-all safety net
        logger.error("Unexpected error executing '%s': %s", tool_name, exc)
        return {"error": f"Unexpected error while running '{tool_name}': {exc}"}


class JarvisLite:
    """
    A minimal stateful assistant: holds conversation history and runs
    the LLM <-> tool-calling loop for each user query.
    """

    def __init__(self):
        if not GROQ_API_KEY:
            raise EngineInitError(
                "GROQ_API_KEY is missing from your .env file. Get a free key "
                "at https://console.groq.com/keys and add it as "
                "GROQ_API_KEY=... in your local .env file."
            )
        try:
            from groq import Groq
        except ImportError as exc:
            raise EngineInitError("The groq package is not installed. Run: pip install groq") from exc

        self.client = Groq(api_key=GROQ_API_KEY)
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask(self, user_query: str) -> str:
        """Run one full turn: user query -> (optional tool round-trip) -> final answer."""
        self.messages.append({"role": "user", "content": user_query})

        for round_num in range(1, MAX_TOOL_CALL_ROUNDS + 1):
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                temperature=LLM_TEMPERATURE,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            message = response.choices[0].message

            if not message.tool_calls:
                # No tool needed -- this is the final natural-language answer.
                final_text = (message.content or "").strip()
                self.messages.append({"role": "assistant", "content": final_text})
                return final_text

            # The LLM decided one or more tools are needed this round.
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
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                    logger.warning("Malformed JSON arguments from LLM for %s", tool_name)

                result = _execute_tool(tool_name, arguments)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

            # Loop again: send the tool result(s) back so the LLM can
            # either produce the final answer or (rarely) call another tool.

        logger.warning("Max tool-call rounds (%d) reached without a final answer.", MAX_TOOL_CALL_ROUNDS)
        fallback = "I wasn't able to finish processing that request after multiple tool calls. Please try rephrasing."
        self.messages.append({"role": "assistant", "content": fallback})
        return fallback

    def reset(self) -> None:
        """Clear conversation history back to just the system prompt."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

"""
Core agent logic.

The Assistant class wraps a Groq chat model (OpenAI-compatible tool-calling
API) with two tools -- calculate and get_weather -- plus a rolling memory of
recent turns. The LLM decides, per message, whether a tool is needed
(intent recognition happens implicitly via function-calling) or whether to
just answer conversationally.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq, GroqError

from .tools import calculate, get_weather

load_dotenv()

SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant with two tools available: "
    "a calculator and a weather lookup. Use the calculator tool for any "
    "arithmetic, algebra, or math question -- translate phrases like "
    "'square root of 625' into a proper expression such as sqrt(625). "
    "Use the weather tool for any question about current conditions or "
    "forecasts in a specific place. For general knowledge, opinions, or "
    "anything that isn't math or weather, answer directly from your own "
    "knowledge without calling a tool. Keep answers concise and natural. "
    "If a tool returns an error, explain the problem to the user in plain "
    "language rather than showing raw error text."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Evaluate a math expression (arithmetic, powers, roots, "
                "trig, logs, factorials, etc.). Always pass a valid Python-"
                "style expression, e.g. '245*78', 'sqrt(625)', "
                "'(3+4)/2**2'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather or a short forecast for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g. 'Lahore' or 'Karachi, PK'.",
                    },
                    "forecast": {
                        "type": "string",
                        "enum": ["true", "false"],
                        "description": "'true' for a ~24h forecast (e.g. 'will it rain tomorrow'), 'false' for current conditions.",
                    },
                },
                "required": ["location"],
            },
        },
    },
]

def _coerce_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return default


_TOOL_IMPL = {
    "calculate": lambda args: calculate(args.get("expression", "")),
    "get_weather": lambda args: get_weather(
        args.get("location", ""), _coerce_bool(args.get("forecast"))
    ),
}


class AssistantError(Exception):
    pass


class Assistant:
    """
    Conversational agent with tool use and rolling memory.

    memory_turns controls how many recent (user, assistant) exchanges are
    kept in context -- older ones are dropped to keep requests small.
    """

    def __init__(self, memory_turns: int = 10, model: str | None = None):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise AssistantError(
                "GROQ_API_KEY is not set. Add it to your .env file (see .env.example)."
            )
        self.client = Groq(api_key=api_key)
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.memory_turns = memory_turns
        self.history: list[dict] = []  # user/assistant turns only (no system, no tool msgs)

    def reset(self):
        self.history = []

    def _trimmed_history(self):
        # Keep only the last N turns (a turn = one user + one assistant message)
        max_messages = self.memory_turns * 2
        return self.history[-max_messages:]

    def ask(self, user_message: str) -> str:
        """Send a message, run any tool calls the model requests, return final text."""
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + self._trimmed_history()
            + [{"role": "user", "content": user_message}]
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1024,
            )
        except GroqError as exc:
            return f"Sorry, I couldn't reach the language model service: {exc}"

        msg = response.choices[0].message

        # Loop in case the model chains tool calls (rare, but handle it)
        loop_guard = 0
        while msg.tool_calls and loop_guard < 4:
            loop_guard += 1
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
                }
            )
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                impl = _TOOL_IMPL.get(name)
                if impl is None:
                    tool_result = {"success": False, "error": f"Unknown tool '{name}'."}
                else:
                    try:
                        tool_result = impl(args)
                    except Exception as exc:  # last-resort guard so the app never crashes
                        tool_result = {"success": False, "error": f"Tool crashed: {exc}"}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": json.dumps(tool_result),
                    }
                )

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=1024,
                )
            except GroqError as exc:
                return f"Sorry, I couldn't reach the language model service: {exc}"
            msg = response.choices[0].message

        final_text = msg.content or "I'm not sure how to respond to that."

        # Update memory
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": final_text})

        return final_text
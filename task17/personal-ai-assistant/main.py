"""
main.py
-------
Entry point for the Personal AI Assistant.

Runs an interactive loop:
  1. Get user input (typed, or spoken if --voice is passed).
  2. Send it to the agent (agent.py), along with conversation memory.
  3. Print the response, and speak it aloud if --voice is enabled.

Usage:
    python main.py                  # text-only chat
    python main.py --voice           # voice input + spoken output
    python main.py --session work    # use a named session (separate memory)
"""

import argparse
import sys
import time
import uuid

import db
from agent import build_agent_executor, build_fallback_llm, AgentInitError
from memory import ConversationMemory
from utils import get_logger

logger = get_logger(__name__)

# Groq's tool-calling models occasionally emit a malformed tool call
# (e.g. the tool name gets concatenated with its JSON arguments), which
# surfaces as a "Failed to call a function" / "which was not in
# request.tools" error. This is a known, intermittent quirk of the
# provider/model combination -- not a bug in the request. Note that at
# temperature 0 the model is deterministic, so retrying the *identical*
# request can reproduce the *identical* failure; a couple of retries
# still helps (Groq's responses aren't perfectly deterministic across
# calls), but if it keeps failing we fall back to a plain conversational
# response with no tools bound, rather than surfacing an error -- most
# requests that trigger this don't strictly need a tool anyway.
_TRANSIENT_TOOL_CALL_MARKERS = (
    "failed to call a function",
    "was not in request.tools",
)
_MAX_RETRIES = 2


def _is_transient_tool_call_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_TOOL_CALL_MARKERS)


def _fallback_plain_response(user_text: str, chat_history) -> str:
    """Answer without any tools, when tool-calling keeps failing."""
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = build_fallback_llm()
    messages = [
        SystemMessage(
            content=(
                "You are a helpful personal AI assistant. Tool access "
                "(calculator, weather, search, files, notes, reminders) is "
                "temporarily unavailable for this turn -- answer as best you "
                "can conversationally, and mention briefly that the user can "
                "retry if they specifically needed a tool-based action "
                "(like checking live weather or saving a note)."
            )
        )
    ]
    messages.extend(chat_history)
    messages.append(HumanMessage(content=user_text))

    response = llm.invoke(messages)
    return (response.content or "").strip() or "I'm not sure how to respond to that."


def invoke_agent_with_retry(agent_executor, user_text: str, chat_history) -> str:
    """
    Invoke the tool-calling agent, retrying a couple of times on transient
    Groq tool-call formatting errors, then falling back to a plain
    no-tools response if it keeps failing.
    """
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 2):  # e.g. 1 initial + 2 retries
        try:
            result = agent_executor.invoke(
                {"input": user_text, "chat_history": chat_history}
            )
            return result.get("output", "").strip() or "I'm not sure how to respond to that."
        except Exception as exc:
            last_exc = exc
            if _is_transient_tool_call_error(exc) and attempt <= _MAX_RETRIES:
                logger.warning(
                    "Transient tool-call error on attempt %d/%d, retrying: %s",
                    attempt, _MAX_RETRIES + 1, exc,
                )
                time.sleep(0.5 * attempt)
                continue
            break

    if _is_transient_tool_call_error(last_exc):
        logger.warning("Tool-calling kept failing; falling back to a plain response.")
        try:
            return _fallback_plain_response(user_text, chat_history)
        except Exception as fallback_exc:
            logger.error("Fallback response also failed: %s", fallback_exc)

    logger.error("Agent execution failed: %s", last_exc)
    return f"Sorry, something went wrong while processing that: {last_exc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Personal AI Assistant")
    parser.add_argument(
        "--voice", action="store_true",
        help="Enable voice input (microphone) and spoken output (text-to-speech).",
    )
    parser.add_argument(
        "--session", type=str, default=None,
        help="Session ID for conversation memory (defaults to a new random session).",
    )
    return parser.parse_args()


def get_user_input(voice_mode: bool) -> str:
    if not voice_mode:
        return input("You: ").strip()

    from voice.speech_to_text import listen_and_transcribe, SpeechToTextError

    print("You (speak now): ", end="", flush=True)
    try:
        text = listen_and_transcribe()
        print(text)
        return text
    except SpeechToTextError as exc:
        print(f"\n  ! Voice input failed: {exc}")
        print("  Falling back to typed input for this turn.")
        return input("You (typed): ").strip()


def speak_response(text: str, voice_mode: bool) -> None:
    if not voice_mode:
        return
    from voice.text_to_speech import speak

    speak(text)


def main() -> int:
    args = parse_args()
    session_id = args.session or str(uuid.uuid4())[:8]

    db.init_db()

    try:
        agent_executor = build_agent_executor()
    except AgentInitError as exc:
        print(f"\nError starting the assistant: {exc}")
        return 1

    memory = ConversationMemory(session_id=session_id)

    print("\nPersonal AI Assistant is ready.")
    print(f"Session: {session_id} | Voice mode: {'ON' if args.voice else 'OFF'}")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_text = get_user_input(args.voice)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        memory.add_user_message(user_text)

        try:
            answer = invoke_agent_with_retry(
                agent_executor, user_text, memory.get_history()[:-1]
            )
        except Exception as exc:
            logger.error("Unexpected error invoking agent: %s", exc)
            answer = f"Sorry, something went wrong while processing that: {exc}"

        memory.add_ai_message(answer)

        print(f"\nAssistant: {answer}\n")
        speak_response(answer, args.voice)


if __name__ == "__main__":
    sys.exit(main() or 0)
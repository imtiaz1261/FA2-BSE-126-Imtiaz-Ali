"""
agent.py
--------
Builds the tool-calling agent: a Groq-hosted LLM that can decide, on
its own, which tool(s) to call based on the user's natural-language
request, then uses the tool results to produce a final answer.

Uses LangChain's standard `create_tool_calling_agent` + `AgentExecutor`
pattern, which relies on the underlying model's native function/tool
calling support (Groq's Llama 3.x models support this).
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE
from tools import ALL_TOOLS
from utils import get_logger

logger = get_logger(__name__)


class AgentInitError(Exception):
    """Raised when the agent cannot be built (e.g. missing API key)."""


SYSTEM_PROMPT = """You are a helpful, friendly personal AI assistant.

You have access to tools for: calculations, current weather, web search,
reading/summarizing PDF/DOCX/TXT files, saving/listing/deleting notes,
and creating/listing/deleting reminders.

Guidelines:
- Use a tool whenever the user's request needs live data, a file, math,
  or persistent storage -- don't guess or make things up.
- For questions about current events, recent news, or facts that may
  have changed since your training, use the web_search tool.
- For anything mathematical, always use the calculator tool rather than
  computing it yourself, so the answer is exact.
- For file-related requests ("summarize this PDF", "what does X say"),
  use the read_file tool with the file name mentioned by the user.
- Keep answers concise and conversational, since some responses may be
  read aloud via text-to-speech.
- If a tool returns an error, explain the issue to the user plainly and
  suggest what they could try instead, rather than pretending it worked.
"""


def build_agent_executor() -> AgentExecutor:
    """Construct the Groq-backed tool-calling agent executor."""
    if not GROQ_API_KEY:
        raise AgentInitError(
            "GROQ_API_KEY is missing from your .env file. Get a free key at "
            "https://console.groq.com/keys and add it as GROQ_API_KEY=... "
            "in your local .env file."
        )

    llm = ChatGroq(model=GROQ_MODEL, temperature=LLM_TEMPERATURE, api_key=GROQ_API_KEY)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=6,
    )
    logger.info("Agent initialized with Groq model '%s' and %d tools.", GROQ_MODEL, len(ALL_TOOLS))
    return executor


def build_fallback_llm():
    """
    Build a plain chat LLM with NO tools bound.

    Used as a graceful fallback: Groq's tool-calling models occasionally
    emit a malformed function call (a known, intermittent quirk of the
    provider) that no amount of retrying the same request will fix at
    temperature 0. Rather than surfacing that as an error, we fall back
    to answering conversationally without tool access for that turn --
    appropriate anyway for requests that don't actually need a tool.
    """
    return ChatGroq(model=GROQ_MODEL, temperature=0.3, api_key=GROQ_API_KEY)
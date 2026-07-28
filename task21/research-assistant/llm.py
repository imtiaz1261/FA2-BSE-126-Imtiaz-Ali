"""
llm.py
------
Single shared Groq chat model instance used by every graph node.
"""

from config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE
from utils import get_logger

logger = get_logger(__name__)


class LLMInitError(Exception):
    """Raised when the LLM can't be initialized (e.g. missing API key)."""


_llm = None


def get_llm():
    global _llm
    if _llm is None:
        if not GROQ_API_KEY:
            raise LLMInitError(
                "GROQ_API_KEY is missing from your .env file. Get a free key at "
                "https://console.groq.com/keys and add it as GROQ_API_KEY=... "
                "in your local .env file."
            )
        from langchain_groq import ChatGroq

        logger.info("Initializing Groq LLM: %s", GROQ_MODEL)
        _llm = ChatGroq(model=GROQ_MODEL, temperature=LLM_TEMPERATURE, api_key=GROQ_API_KEY)
    return _llm

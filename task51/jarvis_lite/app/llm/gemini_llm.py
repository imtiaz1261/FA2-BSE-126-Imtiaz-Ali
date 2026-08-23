"""Google Gemini LLM provider — uses gemini-2.5-flash for answer generation."""

import logging
from typing import Any, Dict, List

import google.generativeai as genai

from app.config.settings import settings
from app.core.exceptions import GenerationError

logger = logging.getLogger(__name__)


class GeminiLLMProvider:
    """LLM provider using Google Gemini API for answer generation."""

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise GenerationError(
                "GEMINI_API_KEY is not set. Cannot initialize Gemini LLM provider."
            )
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_CHAT_MODEL
        self._temperature = settings.LLM_TEMPERATURE

    def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate answer using Gemini."""
        try:
            # Convert OpenAI format to Gemini format if needed
            chat = genai.ChatSession(model=self._model)
            
            # For Gemini, we build the conversation history
            for i, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Gemini uses "user" and "model" roles
                if i < len(messages) - 1:
                    # Add to history
                    if role == "user":
                        chat.history.append(
                            genai.types.ContentDict(role="user", parts=[content])
                        )
                    elif role == "system" or role == "assistant":
                        chat.history.append(
                            genai.types.ContentDict(role="model", parts=[content])
                        )
                else:
                    # Last message - send for generation
                    response = genai.GenerativeModel(self._model).generate_content(
                        content,
                        generation_config=genai.types.GenerationConfig(
                            temperature=self._temperature,
                        ),
                    )
                    return response.text

            return ""
        except Exception as exc:
            logger.exception("Failed to generate answer with Gemini")
            raise GenerationError(f"Gemini generation failed: {exc}") from exc

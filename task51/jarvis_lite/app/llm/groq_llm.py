"""Groq LLM provider — uses Groq API for fast answer generation.

Groq provides faster inference than traditional cloud LLM providers,
making it ideal for real-time chat and fallback responses.
"""

import logging
from typing import Any, Dict, List

from app.config.settings import settings
from app.core.exceptions import GenerationError

logger = logging.getLogger(__name__)


class GroqLLMProvider:
    """LLM provider using Groq API for fast answer generation."""

    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise GenerationError(
                "GROQ_API_KEY is not set. Cannot initialize Groq LLM provider."
            )
        
        try:
            from groq import Groq
            self.client = Groq(api_key=settings.GROQ_API_KEY)
        except ImportError:
            raise GenerationError(
                "groq library not installed. Install with: pip install groq"
            )
        
        self._model = settings.GROQ_MODEL or "mixtral-8x7b-32768"
        self._temperature = settings.LLM_TEMPERATURE

    def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate answer using Groq."""
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=1024,  # Reasonable limit for chat
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("Failed to generate answer with Groq")
            raise GenerationError(f"Groq generation failed: {exc}") from exc

    def generate_simple(self, query: str, system_prompt: str = None) -> str:
        """Generate a simple response without conversation history.
        
        Useful for fallback responses when document search fails.
        
        Args:
            query: User's question
            system_prompt: Optional system prompt for context
            
        Returns:
            Generated response text
        """
        try:
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add user query
            messages.append({
                "role": "user",
                "content": query
            })
            
            response = self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=512,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("Failed to generate simple response with Groq")
            raise GenerationError(f"Groq generation failed: {exc}") from exc

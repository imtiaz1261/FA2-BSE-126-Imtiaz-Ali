"""
services/llm_service.py
=======================
LLM interaction layer — supports Groq (primary) and OpenAI (fallback).

Groq provides free, fast inference for Llama vision models.
OpenAI is used if no Groq key is configured.
"""

from __future__ import annotations

import time
from typing import Generator, List, Optional, Tuple

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import get_settings
from config.constants import GROQ_MODELS
from models.chat import ChatSession
from models.document import UploadedImage
from prompts.templates import PromptBuilder


# ---------------------------------------------------------------------------
# Lazy imports — avoid hard dependency if a package is missing
# ---------------------------------------------------------------------------
def _get_groq_client():
    try:
        from groq import Groq
        settings = get_settings()
        if not settings.groq_key_configured:
            raise ValueError("Groq API key not configured.")
        client = Groq(api_key=settings.groq_api_key.strip())
        logger.info("Groq client initialised | model={}", settings.default_model)
        return client
    except ImportError:
        raise ImportError("groq package not installed. Run: pip install groq")


def _get_openai_client():
    import openai
    settings = get_settings()
    if not settings.openai_key_configured:
        raise ValueError("OpenAI API key not configured.")
    client = openai.OpenAI(api_key=settings.openai_api_key.strip(), timeout=60.0, max_retries=0)
    logger.info("OpenAI client initialised | model={}", settings.default_model)
    return client


# ---------------------------------------------------------------------------
# Singleton clients
# ---------------------------------------------------------------------------
_groq_client = None
_openai_client = None


def get_client(model: Optional[str] = None):
    """
    Return the appropriate client for the given model.
    Prefers Groq if the model is a Groq model and Groq key is configured.
    """
    global _groq_client, _openai_client

    settings = get_settings()
    effective_model = model or settings.default_model

    # Use Groq for Groq models or if Groq key is available and model is unknown
    if effective_model in GROQ_MODELS or (settings.groq_key_configured and effective_model not in ["gpt-4o", "gpt-4o-mini"]):
        if _groq_client is None:
            _groq_client = _get_groq_client()
        return _groq_client, "groq"

    # Fall back to OpenAI
    if settings.openai_key_configured:
        if _openai_client is None:
            _openai_client = _get_openai_client()
        return _openai_client, "openai"

    # Last resort: try Groq anyway
    if settings.groq_key_configured:
        if _groq_client is None:
            _groq_client = _get_groq_client()
        return _groq_client, "groq"

    raise ValueError(
        "No API key configured. Please add GROQ_API_KEY or OPENAI_API_KEY to .env"
    )


# Public aliases for backward compat
def get_openai_client():
    client, _ = get_client()
    return client


def reset_client() -> None:
    """Force re-creation of clients (e.g. after API key change)."""
    global _groq_client, _openai_client
    _groq_client = None
    _openai_client = None
    # Also clear lru_cache on settings
    from config.settings import get_settings
    get_settings.cache_clear()


def validate_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate a Groq or OpenAI API key by making a minimal test call.
    Returns (is_valid, message).
    """
    key = api_key.strip()
    if key.startswith("gsk_"):
        # Groq key
        try:
            from groq import Groq
            client = Groq(api_key=key)
            client.models.list()
            return True, "Groq API key is valid ✅"
        except Exception as exc:
            return False, f"Groq key error: {exc}"
    elif key.startswith("sk-"):
        # OpenAI key
        try:
            import openai
            client = openai.OpenAI(api_key=key, timeout=10.0)
            client.models.list()
            return True, "OpenAI API key is valid ✅"
        except Exception as exc:
            return False, f"OpenAI key error: {exc}"
    else:
        return False, "Unrecognised key format. Groq keys start with gsk_, OpenAI keys with sk-"


# ---------------------------------------------------------------------------
# LLMService
# ---------------------------------------------------------------------------

class LLMService:
    """Handles all LLM calls — streaming Q&A, structured extraction, etc."""

    def __init__(self, openai_client=None, model: Optional[str] = None) -> None:
        self._settings = get_settings()
        self._model = model or self._settings.default_model
        # openai_client param kept for backward compat but we use get_client()
        self._forced_client = openai_client

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value
        logger.info("Model switched to: {}", value)

    def _client_and_provider(self):
        if self._forced_client:
            return self._forced_client, "openai"
        return get_client(self._model)

    # ------------------------------------------------------------------
    # Streaming Q&A
    # ------------------------------------------------------------------
    def stream_answer(
        self,
        image: UploadedImage,
        question: str,
        session: ChatSession,
    ) -> Generator[str, None, None]:
        """Stream an answer token-by-token (ChatGPT-style)."""
        is_followup = session.message_count > 0
        history = session.get_openai_history()
        client, provider = self._client_and_provider()

        # Build messages — use vision or text-only depending on provider capability
        messages = self._build_messages(
            image=image,
            question=question,
            history=history,
            is_followup=is_followup,
            provider=provider,
        )

        try:
            start = time.monotonic()
            stream = client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._settings.max_tokens,
                temperature=self._settings.temperature,
                stream=True,
            )

            full_response = ""
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_response += delta.content
                    yield delta.content

            latency_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "Stream complete | chars={} latency={}ms model={} provider={}",
                len(full_response), latency_ms, self._model, provider,
            )

        except Exception as exc:
            err_str = str(exc)
            logger.error("Streaming error ({}): {}", provider, exc)
            if "401" in err_str or "invalid_api_key" in err_str or "authentication" in err_str.lower():
                yield "❌ **Authentication failed.** Please check your API key in the Settings panel."
            elif "rate" in err_str.lower() or "429" in err_str:
                yield "⚠️ **Rate limit reached.** Please wait a moment and try again."
            elif "connection" in err_str.lower():
                yield "🔌 **Connection error.** Please check your internet connection."
            elif "model_not_found" in err_str or "404" in err_str:
                yield f"❌ **Model not found:** `{self._model}`. Please select a different model in Settings."
            else:
                yield f"❌ **Error:** {exc}"

    def _build_messages(
        self,
        image: UploadedImage,
        question: str,
        history: List[dict],
        is_followup: bool,
        provider: str,
    ) -> List[dict]:
        """
        Build message payload.
        - For vision-capable providers: include image_url content block.
        - For text-only providers (Groq text models): embed OCR text instead.
        """
        # Detect if the model supports vision
        is_vision_model = self._model in [
            "llama-3.2-11b-vision-preview",
            "llama-3.2-90b-vision-preview",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1",
        ]

        if is_vision_model:
            # Standard multimodal path
            if PromptBuilder.is_json_request(question):
                return PromptBuilder.json_on_demand(image.data_uri, history)
            return PromptBuilder.question_with_history(
                image.data_uri, question, history, is_followup
            )

        # Text-only path — embed OCR text in the user message
        from services.ocr_service import get_image_description_prompt
        from prompts.system_prompts import get_system_prompt

        ocr_context = get_image_description_prompt(
            image.base64_data,
            image.metadata.filename,
        )

        messages: List[dict] = [
            {"role": "system", "content": get_system_prompt("qa")},
        ]
        # Add history (text only)
        messages.extend(history)

        # Current user turn with OCR context embedded
        full_question = f"{ocr_context}\n\nUser question: {question}"
        messages.append({"role": "user", "content": full_question})
        return messages

    # ------------------------------------------------------------------
    # Non-streaming call
    # ------------------------------------------------------------------
    def call(
        self,
        messages: List[dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> Tuple[str, int]:
        """Single non-streaming completion call. Returns (text, tokens)."""
        client, provider = self._client_and_provider()

        # Strip image_url blocks from messages if model doesn't support vision
        is_vision_model = self._model in [
            "llama-3.2-11b-vision-preview",
            "llama-3.2-90b-vision-preview",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4.1",
        ]

        if not is_vision_model:
            messages = _strip_image_blocks_from_messages(messages)

        kwargs = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens or self._settings.max_tokens,
            "temperature": temperature if temperature is not None else self._settings.temperature,
        }
        if json_mode and provider == "openai":
            kwargs["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        response = client.chat.completions.create(**kwargs)
        latency = int((time.monotonic() - start) * 1000)

        content = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else 0

        logger.debug(
            "LLM call | tokens={} latency={}ms model={} provider={}",
            tokens, latency, self._model, provider,
        )
        return content, tokens

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------
    def extract_structured(self, image: UploadedImage, document_type: str) -> Tuple[str, int]:
        messages = PromptBuilder.extract_structured(image.data_uri, document_type)
        return self.call(messages, max_tokens=2048, temperature=0.0)

    def extract_full_text(self, image: UploadedImage) -> Tuple[str, int]:
        messages = PromptBuilder.ocr_extract(image.data_uri)
        return self.call(messages, max_tokens=2048, temperature=0.0)

    def summarize(self, image: UploadedImage) -> Tuple[str, int]:
        messages = PromptBuilder.summarize(image.data_uri)
        return self.call(messages, max_tokens=512, temperature=0.3)

    def validate_document(self, image: UploadedImage) -> Tuple[str, int]:
        messages = PromptBuilder.validate_document(image.data_uri)
        return self.call(messages, max_tokens=1024, temperature=0.1)

    def regenerate(
        self,
        image: UploadedImage,
        session: ChatSession,
    ) -> Generator[str, None, None]:
        """Re-run the last user question."""
        last_user_msg = None
        for msg in reversed(session.messages):
            if msg.is_user:
                last_user_msg = msg
                break

        if not last_user_msg:
            yield "No previous question to regenerate."
            return

        if session.messages and session.messages[-1].is_assistant:
            session.messages.pop()

        yield from self.stream_answer(image, last_user_msg.content, session)


# ---------------------------------------------------------------------------
# Convenience factory for Streamlit
# ---------------------------------------------------------------------------

def create_llm_service(model: Optional[str] = None) -> Optional[LLMService]:
    """Create an LLMService instance, or return None if no key is configured."""
    try:
        settings = get_settings()
        if not settings.api_key_configured:
            logger.warning("No API key configured — LLMService not created.")
            return None
        svc = LLMService(model=model)
        # Quick connectivity test — just instantiate client
        get_client(model or settings.default_model)
        return svc
    except Exception as exc:
        logger.error("LLMService creation failed: {}", exc)
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_image_blocks_from_messages(messages: List[dict]) -> List[dict]:
    """
    Remove image_url content blocks from messages for text-only models.
    Converts multimodal content lists to plain text strings.
    """
    cleaned = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            # Keep only text blocks
            text_parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            new_content = "\n".join(text_parts).strip()
            cleaned.append({**msg, "content": new_content})
        else:
            cleaned.append(msg)
    return cleaned

"""
voice/text_to_speech.py
--------------------------
Text-to-speech using `pyttsx3` -- runs fully offline, no API key or
internet connection required. Wraps engine creation so failures (e.g.
no audio driver available in a headless/server environment) degrade
gracefully instead of crashing the assistant.
"""

from utils import get_logger

logger = get_logger(__name__)

_engine = None


class TextToSpeechError(Exception):
    """Raised when the TTS engine can't be initialized or can't speak."""


def _get_engine():
    global _engine
    if _engine is None:
        try:
            import pyttsx3
            from config import TTS_RATE, TTS_VOLUME
        except ImportError as exc:
            raise TextToSpeechError(
                "pyttsx3 is not installed. Run: pip install pyttsx3"
            ) from exc

        try:
            _engine = pyttsx3.init()
            _engine.setProperty("rate", TTS_RATE)
            _engine.setProperty("volume", TTS_VOLUME)
        except Exception as exc:
            raise TextToSpeechError(f"Failed to initialize TTS engine: {exc}") from exc
    return _engine


def speak(text: str) -> None:
    """Speak the given text aloud. Silently logs (rather than raises) on
    failure so a broken audio setup never blocks the text response."""
    if not text.strip():
        return
    try:
        engine = _get_engine()
        engine.say(text)
        engine.runAndWait()
    except TextToSpeechError as exc:
        logger.warning("Text-to-speech unavailable: %s", exc)
    except Exception as exc:
        logger.warning("Text-to-speech failed: %s", exc)

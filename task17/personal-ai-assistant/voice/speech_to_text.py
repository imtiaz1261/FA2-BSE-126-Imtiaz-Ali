"""
voice/speech_to_text.py
-------------------------
Voice input using the `SpeechRecognition` library. Uses Google's free
public Web Speech API endpoint via `recognize_google()` -- no API key
required, but it does need an internet connection and a working
microphone (via PyAudio).
"""

from utils import get_logger

logger = get_logger(__name__)


class SpeechToTextError(Exception):
    """Raised when microphone capture or recognition fails."""


def listen_and_transcribe(timeout: int = 8, phrase_time_limit: int = 15) -> str:
    """
    Listen on the default microphone and return the transcribed text.

    Raises
    ------
    SpeechToTextError
        If no microphone is available, nothing is heard in time, or
        the audio couldn't be transcribed.
    """
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise SpeechToTextError(
            "SpeechRecognition is not installed. Run: pip install SpeechRecognition pyaudio"
        ) from exc

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            logger.info("Listening for voice input...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
    except OSError as exc:
        raise SpeechToTextError(
            f"No microphone available or audio device error: {exc}"
        ) from exc
    except sr.WaitTimeoutError:
        raise SpeechToTextError("No speech detected within the timeout period.")

    try:
        text = recognizer.recognize_google(audio)
        logger.info("Transcribed voice input: %r", text)
        return text
    except sr.UnknownValueError:
        raise SpeechToTextError("Could not understand the audio.")
    except sr.RequestError as exc:
        raise SpeechToTextError(f"Speech recognition service error: {exc}")

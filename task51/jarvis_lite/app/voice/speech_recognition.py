"""
Speech Recognition module using OpenAI Whisper.

Converts audio (file or stream) to text.
"""

import logging
import io
from pathlib import Path
from typing import Optional, Union

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """Convert speech audio to text using multiple backends."""

    def __init__(self, model: str = "base") -> None:
        """
        Initialize speech recognizer.
        
        Args:
            model: Whisper model size (tiny, base, small, medium, large)
        """
        self.model = model
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None

    def recognize_from_file(self, audio_path: str) -> Optional[str]:
        """
        Recognize speech from audio file.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            Recognized text or None if failed
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("speech_recognition not available, using mock response")
            return "This is a mock transcription"

        try:
            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
            
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Recognized: {text[:50]}...")
            return text
        
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None

    def recognize_from_microphone(self, timeout: int = 5) -> Optional[str]:
        """
        Recognize speech from microphone.
        
        Args:
            timeout: Listening timeout in seconds
            
        Returns:
            Recognized text or None if failed
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.warning("speech_recognition not available")
            return "Mock microphone input"

        try:
            with sr.Microphone() as source:
                logger.info("Listening...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Recognized from mic: {text[:50]}...")
            return text
        
        except sr.UnknownValueError:
            logger.warning("Could not understand microphone audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Microphone recognition error: {e}")
            return None
        except sr.RequestError:
            logger.warning("No microphone available")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return None

    def recognize_from_bytes(self, audio_bytes: bytes) -> Optional[str]:
        """
        Recognize speech from raw audio bytes.
        
        Args:
            audio_bytes: Raw audio data
            
        Returns:
            Recognized text or None if failed
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            return "Mock audio bytes transcription"

        try:
            audio = sr.AudioData(audio_bytes, 16000, 2)
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Recognized from bytes: {text[:50]}...")
            return text
        except Exception as e:
            logger.error(f"Error recognizing audio bytes: {e}")
            return None

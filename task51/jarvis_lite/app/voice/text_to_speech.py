"""
Text-to-Speech module using multiple backends.

Converts text to audio (file, stream, or chunked/streaming for real-time playback).
"""

import logging
import io
from pathlib import Path
from typing import Optional, Generator

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Convert text to speech using multiple backends."""

    def __init__(self, backend: str = "gtts", language: str = "en") -> None:
        """
        Initialize TTS engine.
        
        Args:
            backend: "gtts" (Google TTS, free) or "pyttsx3" (local, offline)
            language: Language code (e.g., "en", "hi", "es")
        """
        self.backend = backend
        self.language = language
        
        if backend == "pyttsx3" and PYTTSX3_AVAILABLE:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)  # Speech rate
        else:
            self.engine = None

    def speak_to_file(self, text: str, output_path: str) -> bool:
        """
        Convert text to speech and save to file.
        
        Args:
            text: Text to convert
            output_path: Output file path (MP3)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.backend == "gtts" and GTTS_AVAILABLE:
                tts = gTTS(text=text, lang=self.language, slow=False)
                tts.save(output_path)
                logger.info(f"TTS saved to {output_path}")
                return True
            
            elif self.backend == "pyttsx3" and PYTTSX3_AVAILABLE:
                self.engine.save_to_file(text, output_path)
                self.engine.runAndWait()
                logger.info(f"TTS (pyttsx3) saved to {output_path}")
                return True
            
            else:
                logger.warning("No TTS backend available")
                return False
        
        except Exception as e:
            logger.exception(f"TTS error: {e}")
            return False

    def speak_to_bytes(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech and return as bytes.
        
        Args:
            text: Text to convert
            
        Returns:
            Audio bytes or None if failed
        """
        try:
            if self.backend == "gtts" and GTTS_AVAILABLE:
                tts = gTTS(text=text, lang=self.language, slow=False)
                audio_bytes = io.BytesIO()
                tts.write_to_fp(audio_bytes)
                audio_bytes.seek(0)
                logger.info(f"TTS bytes generated ({len(audio_bytes.getvalue())} bytes)")
                return audio_bytes.getvalue()
            
            elif self.backend == "pyttsx3" and PYTTSX3_AVAILABLE:
                temp_path = "temp_audio.wav"
                self.engine.save_to_file(text, temp_path)
                self.engine.runAndWait()
                with open(temp_path, "rb") as f:
                    return f.read()
            
            else:
                logger.warning("No TTS backend available")
                return None
        
        except Exception as e:
            logger.exception(f"TTS bytes error: {e}")
            return None

    def speak(self, text: str) -> bool:
        """
        Speak text directly (blocking).
        
        Args:
            text: Text to speak
            
        Returns:
            True if successful
        """
        try:
            if self.backend == "pyttsx3" and PYTTSX3_AVAILABLE:
                self.engine.say(text)
                self.engine.runAndWait()
                logger.info("Text spoken successfully")
                return True
            else:
                logger.warning("Direct speech not available with this backend")
                return False
        
        except Exception as e:
            logger.exception(f"Speak error: {e}")
            return False

    def set_voice(self, voice_id: int = 0) -> None:
        """
        Set voice (pyttsx3 only).
        
        Args:
            voice_id: 0 for male, 1 for female
        """
        if PYTTSX3_AVAILABLE and self.engine:
            try:
                voices = self.engine.getProperty('voices')
                if voice_id < len(voices):
                    self.engine.setProperty('voice', voices[voice_id].id)
                    logger.info(f"Voice set to {voices[voice_id].name}")
            except Exception as e:
                logger.warning(f"Could not set voice: {e}")

    def set_rate(self, rate: int = 150) -> None:
        """
        Set speech rate (pyttsx3 only).
        
        Args:
            rate: Words per minute (default: 150)
        """
        if PYTTSX3_AVAILABLE and self.engine:
            self.engine.setProperty('rate', rate)
            logger.info(f"Speech rate set to {rate}")

    def speak_to_chunks(self, text: str, chunk_size: int = 100) -> Generator[bytes, None, None]:
        """
        Stream text-to-speech as audio chunks (for real-time playback).
        
        Splits text into sentences and generates audio for each chunk,
        yielding audio bytes as they become available.
        
        Args:
            text: Text to convert to speech
            chunk_size: Approximate number of characters per chunk (for sentence splitting)
            
        Yields:
            Audio bytes chunks as they are generated
        """
        try:
            if not GTTS_AVAILABLE:
                logger.warning("gTTS not available for streaming")
                return
            
            # Split text into sentences for streaming
            sentences = self._split_into_sentences(text)
            
            if not sentences:
                logger.warning("No sentences to convert")
                return
            
            logger.info(f"Streaming {len(sentences)} sentence chunks")
            
            for i, sentence in enumerate(sentences):
                if not sentence.strip():
                    continue
                
                try:
                    # Generate audio for this sentence
                    tts = gTTS(text=sentence.strip(), lang=self.language, slow=False)
                    audio_buffer = io.BytesIO()
                    tts.write_to_fp(audio_buffer)
                    audio_bytes = audio_buffer.getvalue()
                    
                    if audio_bytes and len(audio_bytes) > 0:
                        logger.debug(f"Generated chunk {i+1}/{len(sentences)} ({len(audio_bytes)} bytes)")
                        yield audio_bytes
                    
                except Exception as e:
                    logger.warning(f"Failed to generate audio for chunk {i+1}: {e}")
                    continue
        
        except Exception as e:
            logger.exception(f"Streaming TTS error: {e}")

    @staticmethod
    def _split_into_sentences(text: str, max_length: int = 200) -> list:
        """
        Split text into sentences for streaming.
        
        Google TTS has limits on text length, so we split into manageable chunks.
        
        Args:
            text: Text to split
            max_length: Maximum characters per sentence (gTTS limit ~200)
            
        Returns:
            List of sentence chunks
        """
        # Simple sentence splitting by common delimiters
        import re
        
        # Split by sentence-ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # If sentences are too long, split further by comma
        result = []
        for sentence in sentences:
            if len(sentence) <= max_length:
                result.append(sentence)
            else:
                # Split by commas for longer sentences
                parts = sentence.split(', ')
                for part in parts:
                    if len(part) <= max_length:
                        result.append(part)
                    else:
                        # If still too long, split into chunks
                        for chunk in [part[i:i+max_length] for i in range(0, len(part), max_length)]:
                            result.append(chunk)
        
        return [s for s in result if s.strip()]

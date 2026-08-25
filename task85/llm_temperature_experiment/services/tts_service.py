from pathlib import Path
from typing import Optional

import pyttsx3


class TTSServiceError(Exception):
    """Raised when local text-to-speech fails."""


class TTSService:
    """Provider-independent wrapper around the local pyttsx3 engine."""

    def __init__(self):
        try:
            self.engine = pyttsx3.init()
        except Exception as exc:
            raise TTSServiceError(
                "Could not initialize the local TTS engine. "
                "Check that a system speech engine/voice is installed."
            ) from exc

    def get_voices(self):
        try:
            voices = self.engine.getProperty("voices") or []
            result = []

            for index, voice in enumerate(voices):
                voice_id = getattr(voice, "id", "")
                name = getattr(voice, "name", None) or f"Voice {index + 1}"
                languages = getattr(voice, "languages", None) or []

                language_text = ""
                if languages:
                    language_text = " • " + ", ".join(
                        str(item) for item in languages[:2]
                    )

                result.append({
                    "id": voice_id,
                    "label": f"{name}{language_text}",
                })

            return result

        except Exception as exc:
            raise TTSServiceError(
                f"Unable to read installed voices: {exc}"
            ) from exc

    def generate(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
        rate: int = 165,
        volume: float = 1.0,
    ) -> Path:
        if not text.strip():
            raise TTSServiceError("Text cannot be empty.")

        try:
            # A fresh engine avoids stale state between generations.
            self.engine.stop()

            if voice_id:
                self.engine.setProperty("voice", voice_id)

            self.engine.setProperty("rate", rate)
            self.engine.setProperty("volume", volume)

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.engine.save_to_file(text, str(output_path))
            self.engine.runAndWait()

            if not output_path.exists():
                raise TTSServiceError(
                    "The speech engine did not create the audio file."
                )

            return output_path

        except TTSServiceError:
            raise
        except Exception as exc:
            raise TTSServiceError(
                f"TTS generation failed: {exc}"
            ) from exc

"""
Voice-enabled AI assistant, Siri-style.

Pipeline for every turn of the conversation:

    Microphone (push-to-talk: press Enter to start, Enter again to stop)
        |  sounddevice records raw audio while you're "recording"
        v
    Speech-to-Text  -- Groq's hosted Whisper model transcribes the audio to text
        v
    LLM (intent + response) -- Groq's Llama model reads the text + conversation
        |                      history, and generates a natural reply
        v
    Text-to-Speech -- edge-tts speaks the reply with a natural neural voice
        v
    back to Microphone, loop continues (continuous conversation, like Siri)

Everything here is free: Groq's API has no cost for the models used, and
edge-tts uses Microsoft Edge's free neural voices (same engine behind
Edge's "Read Aloud" feature) — no API key, no cost, much more natural
sounding than the offline pyttsx3/SAPI5 engine. Playback uses Windows'
built-in winmm.dll via ctypes, so no third-party audio-playback package
is required at all — avoiding the compile issues that PyAudio, playsound,
and pygame all hit on very new Python versions like 3.14.
"""

import argparse
import asyncio
import os
import tempfile
import wave

import ctypes
import edge_tts
import numpy as np
import sounddevice as sd
from openai import OpenAI

try:
    from secret_key import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = None

if not GROQ_API_KEY or "your-groq-key-here" in GROQ_API_KEY:
    raise SystemExit("Add your real Groq key to secret_key.py first.")

CHAT_MODEL = "llama-3.3-70b-versatile"
STT_MODEL = "whisper-large-v3"
SAMPLE_RATE = 16000  # Whisper expects 16kHz mono audio

# Natural-sounding free neural voice. Try others with --list-voices, e.g.
# "en-US-GuyNeural" (male), "en-GB-SoniaNeural" (British), etc.
TTS_VOICE = "en-US-AriaNeural"

# Below this average volume, we assume the mic didn't actually pick up
# speech (this is what causes Whisper to "hallucinate" words like "you"
# or "Thank you." on silence) and skip sending it to the API.
SILENCE_THRESHOLD = 150

SYSTEM_PROMPT = (
    "You are a helpful, friendly voice assistant, similar to Siri or "
    "Google Assistant. Keep replies short (1-3 sentences), natural, and "
    "conversational, since they will be read aloud. Never use markdown, "
    "bullet points, or special formatting — plain spoken sentences only."
)

EXIT_WORDS = {"exit", "quit", "goodbye", "good bye", "bye", "stop listening", "stop"}


def play_mp3_windows(path: str) -> None:
    """Plays an MP3 file using Windows' built-in Media Control Interface
    (winmm.dll), accessed through ctypes. This needs no pip package at
    all — winmm.dll ships with every copy of Windows — which sidesteps
    the compile issues that PyAudio/playsound/pygame hit on very new
    Python versions like 3.14 (no wheels published for them yet).

    This is the same underlying mechanism the `playsound` library uses
    internally on Windows, just called directly.
    """
    winmm = ctypes.windll.winmm
    alias = "voice_assistant_reply"

    # "open" loads the file under a short alias name so later commands
    # can refer to it without repeating the full path.
    winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
    # "play ... wait" blocks until playback finishes, so speak() doesn't
    # return before the audio is actually done.
    winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
    # "close" releases the file handle so it can be deleted afterward.
    winmm.mciSendStringW(f'close {alias}', None, 0, None)


class VoiceAssistant:
    def __init__(self, user_name: str, input_device=None):
        self.user_name = user_name
        self.input_device = input_device
        self.client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

        # Conversation memory — the LLM sees this whole history each turn,
        # so it can handle follow-up questions naturally.
        self.conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

    # ------------------------------------------------------------------
    # Text-to-Speech (edge-tts — free neural voice, needs internet)
    # ------------------------------------------------------------------
    async def _synthesize(self, text: str, path: str) -> None:
        communicate = edge_tts.Communicate(text, TTS_VOICE)
        await communicate.save(path)

    def speak(self, text: str) -> None:
        print(f"Assistant: {text}")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        try:
            asyncio.run(self._synthesize(text, tmp_path))
            play_mp3_windows(tmp_path)
        except Exception as e:
            print(f"[TTS error, printing only] {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ------------------------------------------------------------------
    # Recording (push-to-talk)
    # ------------------------------------------------------------------
    def record_audio(self, path: str) -> np.ndarray:
        """Records from the microphone until the user presses Enter.
        Returns the raw audio samples so the caller can check the volume."""
        frames = []

        def callback(indata, frames_count, time_info, status):
            frames.append(indata.copy())

        print("\nPress Enter to start speaking...")
        input()
        print("Recording... press Enter again to stop.")

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            device=self.input_device,
            callback=callback,
        )
        stream.start()
        input()  # blocks here until the user presses Enter again
        stream.stop()
        stream.close()

        if not frames:
            audio_data = np.zeros((0,), dtype="int16")
        else:
            audio_data = np.concatenate(frames, axis=0)

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16 = 2 bytes per sample
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        return audio_data

    # ------------------------------------------------------------------
    # Speech-to-Text
    # ------------------------------------------------------------------
    def listen(self) -> str:
        """Records a push-to-talk clip, then transcribes it with Groq's
        hosted Whisper model. Returns "" if the recording looks silent,
        instead of sending near-empty audio (which causes Whisper to
        hallucinate filler words)."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            audio_data = self.record_audio(tmp_path)

            if len(audio_data) == 0:
                return ""

            volume = np.abs(audio_data.astype(np.int32)).mean()
            if volume < SILENCE_THRESHOLD:
                print(f"(Recording was too quiet — avg volume {volume:.1f}, "
                      f"threshold {SILENCE_THRESHOLD}. Check your microphone: "
                      f"run with --list-devices to see available mics, or "
                      f"--device <index> to pick the right one.)")
                return ""

            with open(tmp_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=STT_MODEL,
                    file=audio_file,
                )
            return transcript.text.strip()
        finally:
            os.remove(tmp_path)

    # ------------------------------------------------------------------
    # LLM — understands intent, generates the reply
    # ------------------------------------------------------------------
    def get_response(self, user_text: str) -> str:
        self.conversation.append({"role": "user", "content": user_text})

        completion = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=self.conversation,
        )
        reply = completion.choices[0].message.content.strip()

        self.conversation.append({"role": "assistant", "content": reply})
        return reply

    # ------------------------------------------------------------------
    # Main loop — continuous conversation
    # ------------------------------------------------------------------
    def run(self) -> None:
        self.speak(f"Welcome, {self.user_name}. How can I help you today?")

        while True:
            try:
                user_text = self.listen()
            except Exception as e:
                print(f"[Error while listening] {e}")
                self.speak("Sorry, I didn't catch that. Could you try again?")
                continue

            if not user_text:
                print("(No speech detected, try again)")
                continue

            print(f"{self.user_name}: {user_text}")

            if any(word in user_text.lower() for word in EXIT_WORDS):
                self.speak("Goodbye! Have a great day.")
                break

            try:
                reply = self.get_response(user_text)
            except Exception as e:
                print(f"[Error getting response] {e}")
                self.speak("Sorry, I ran into a problem. Please try again.")
                continue

            self.speak(reply)


def list_input_devices() -> None:
    print("\nAvailable audio input devices:\n")
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            marker = " (default)" if i == sd.default.device[0] else ""
            print(f"  [{i}] {d['name']}{marker}")
    print("\nRun again with: python voice_assistant.py --device <index> --name YourName\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Voice-enabled AI assistant")
    parser.add_argument("--name", default="there", help="Your name, for the greeting")
    parser.add_argument("--device", type=int, default=None, help="Input device index to use (see --list-devices)")
    parser.add_argument("--list-devices", action="store_true", help="List available microphones and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_devices:
        list_input_devices()
        return

    assistant = VoiceAssistant(user_name=args.name, input_device=args.device)
    try:
        assistant.run()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
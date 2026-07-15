# Task 10 — Voice-Enabled AI Assistant

A Siri-style voice assistant: it listens to you, transcribes your speech,
understands what you want using an LLM, and speaks a natural reply back —
in a continuous loop, so you can have a real back-and-forth conversation.

## Pipeline

```
Microphone (push-to-talk: press Enter to start, Enter again to stop)
   |  sounddevice records raw audio while you're "recording"
   v
Speech-to-Text   -- Groq's hosted Whisper model transcribes audio -> text
   v
LLM (Groq Llama) -- reads the text + full conversation history,
   |                generates a short, natural reply
   v
Text-to-Speech (edge-tts) -- speaks the reply with a natural neural voice
   v
back to Microphone -- loop continues until you say "exit"/"stop"/"goodbye"
```

Everything here is **free**: Groq's hosted models (Whisper for
transcription, Llama for the chat/reasoning) currently have no cost, and
`edge-tts` uses Microsoft Edge's free neural text-to-speech voices (the
same engine behind Edge's "Read Aloud" feature) — no API key, no cost,
and far more natural sounding than the older offline `pyttsx3`/SAPI5
engine (which is the classic robotic Windows voice).

**Why push-to-talk instead of automatic silence detection?** `PyAudio`
needs to be compiled from source unless a precompiled wheel exists for
your exact Python version, and very new Python releases (3.13/3.14) often
don't have one yet, causing install failures. `sounddevice` ships
prebuilt binaries, so there's nothing to compile — the trade-off is you
press Enter to start/stop talking instead of it auto-detecting silence.

## Files

| File                  | Purpose                                     |
|-------------------------|------------------------------------------------|
| `voice_assistant.py`  | Main script — run this                       |
| `requirements.txt`    | Python dependencies                          |
| `secret_key.py`       | Your API key (never commit this file)        |
| `.gitignore`          | Keeps `secret_key.py` out of version control  |

## Setup

1. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```
   This should install cleanly on Windows with no compiler needed.

3. **Add your API key** in `secret_key.py`.

## Before your first real run: find the right microphone

If your last run showed garbage transcriptions like "you" or "Thank
you." repeatedly, your mic almost certainly wasn't being captured — that
specific pattern is what Whisper produces when it receives silence, not
real speech.

List your available microphones:
```
python voice_assistant.py --list-devices
```

This prints something like:
```
Available audio input devices:

  [1] Microphone Array (Realtek Audio) (default)
  [3] Headset Microphone (Bluetooth)
```

If the "(default)" device isn't the mic you're actually using (e.g.
you're on a headset but a laptop's built-in array mic is marked
default), run the assistant with the correct device index:
```
python voice_assistant.py --name Imtiaz --device 3
```

Also double check: **Windows Settings → Privacy & security → Microphone**
— make sure "Let apps access your microphone" is on, and that your
terminal/Python isn't blocked there.

## Usage

```
python voice_assistant.py --name Imtiaz
```

It will greet you: *"Welcome, Imtiaz. How can I help you today?"* — then
prompt you to press Enter to start talking. Press Enter, speak clearly
into your mic, then press Enter again to stop recording. It transcribes
what you said, sends it to the LLM, and speaks the reply — then prompts
you again for the next turn. Say **"exit"**, **"stop"**, **"quit"**, or
**"goodbye"** during your turn to end the conversation.

If a recording comes back too quiet, the assistant now tells you instead
of silently sending near-empty audio to Whisper:
```
(Recording was too quiet — avg volume 4.2, threshold 150. Check your
microphone: run with --list-devices to see available mics, or --device
<index> to pick the right one.)
```

## How each piece works

- **`self.record_audio(path)`** — starts a `sounddevice` input stream when
  you press Enter, collects raw audio chunks in a background callback,
  and stops when you press Enter again, saving everything to a WAV file.
- **Volume check** — after recording, the average amplitude of the audio
  is measured. If it's below a threshold, the clip is treated as silence
  and discarded *before* being sent to Whisper — this is what prevents
  the "hallucinated" transcriptions like "you" you saw before.
- **`self.client.audio.transcriptions.create(model="whisper-large-v3", ...)`**
  — sends the recorded audio to Groq's Whisper model, which returns the
  transcribed text.
- **`self.client.chat.completions.create(...)`** — sends your transcribed
  text plus the full conversation history to Groq's Llama model, so it
  can understand follow-up questions in context.
- **`edge_tts.Communicate(text, TTS_VOICE).save(path)`** — generates a
  natural-sounding neural speech MP3 from the reply text, using Edge's
  free cloud TTS service (this step needs an internet connection).
- **`pygame.mixer.music`** — loads and plays that MP3 out loud through
  your speakers, then waits until playback finishes before continuing.
- **`self.conversation`** — a running list of every message exchanged,
  which is what makes this a real *conversation* rather than a series of
  disconnected one-off questions.

## Trying different voices

`TTS_VOICE = "en-US-AriaNeural"` near the top of the script controls the
voice. Some other natural-sounding free options:
- `"en-US-GuyNeural"` — male, US English
- `"en-GB-SoniaNeural"` — female, British English
- `"en-US-JennyNeural"` — female, US English, warmer tone

To see the full list available, run this in your terminal (after
installing edge-tts):
```
edge-tts --list-voices
```

## Limitations & things to know

- This assistant answers questions and chats — it does not actually
  control your laptop (no "open Spotify" / "set a timer" actions). Adding
  real actions is the natural next step (see below).
- `edge-tts` requires an internet connection (it calls Microsoft's free
  cloud service) — it's not fully offline like `pyttsx3` was.
- Accuracy depends on your microphone quality, background noise, and
  making sure the correct input device is selected (see the device
  selection section above).
- If Groq's free tier rate limit is hit during a long session, requests
  may briefly fail — the assistant will say "Sorry, I ran into a problem"
  and keep listening rather than crashing.

## Extending this into "real" actions (optional next steps)

- **Wake word detection**: add a lightweight offline wake-word library
  (e.g. `pvporcupine`) so it only starts listening after you say a
  trigger phrase.
- **Real task execution**: give the LLM "tools" (function calling) for
  things like opening apps, checking the time, or setting reminders, and
  execute those functions locally when the model requests them.
- **Faster response**: switch to Groq's `llama-3.1-8b-instant` model for
  lower latency if `llama-3.3-70b-versatile` feels slow on your machine.
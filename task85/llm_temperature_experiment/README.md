# 🎙️ Task 85 — Smart Voice Generator

A professional Streamlit-based Text-to-Speech application built with **Python 3.11+**, **Streamlit**, and **pyttsx3**. It converts user-provided text into speech locally and generates a WAV audio file that can be played or downloaded directly from the interface.

## Features

* Large text input area
* Character and word counter
* 5,000-character input validation
* One-click speech generation
* Browser-based audio playback
* WAV file download
* System voice selection
* Adjustable speech speed
* Volume control
* Clear input functionality
* Friendly error handling
* Modular TTS service architecture
* Offline/local speech processing
* No API key required

## Project Structure

```text
smart_voice_generator/
│
├── app.py
├── services/
│   ├── __init__.py
│   └── voice_service.py
├── utils/
│   ├── __init__.py
│   └── validators.py
├── audio/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Requirements

* Python 3.11 or newer
* Windows, macOS, or Linux
* At least one system-installed speech/TTS voice

## Windows Installation

Open PowerShell inside the project directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Start the application:

```powershell
streamlit run app.py
```

Open the Streamlit URL, normally:

```text
http://localhost:8501
```

## macOS/Linux Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

On some Linux distributions, `pyttsx3` requires an additional system speech engine such as `espeak-ng`.

## How It Works

```text
User enters text
       ↓
Input validation
       ↓
Voice, speed & volume configuration
       ↓
VoiceService
       ↓
pyttsx3 local TTS engine
       ↓
WAV audio generation
       ↓
Streamlit audio player
       ↓
Audio download
```

## Adding Another TTS Provider

The speech-generation logic is separated inside:

```text
services/voice_service.py
```

This makes the application easier to extend with other providers such as **gTTS or cloud-based TTS APIs** without placing provider-specific code inside `app.py`.

## Playback

The application uses Streamlit's native audio component for playback. Play, pause, seek, and volume controls are handled by the user's browser.

## Troubleshooting

### `No module named pyttsx3`

Install the package manually:

```powershell
pip install pyttsx3
```

### Windows voices are unavailable

Open Windows speech settings and verify that at least one speech voice is installed.

### `pywin32` issues on Windows

Run:

```powershell
pip install --upgrade pywin32
```

Then restart the application:

```powershell
streamlit run app.py
```

### WAV file is not generated

Verify that a system TTS voice is installed and working correctly. Test the operating system's speech functionality before running the application again.

## Privacy

This version uses **local pyttsx3 processing**, so the entered text is not intentionally transmitted to an external TTS service.

If a cloud-based provider is added later, store API credentials in environment variables or a `.env` file rather than directly inside the source code.

**Task 85 demonstrates how Python, Streamlit, and local TTS technology can be combined to create a simple, private, and user-friendly AI voice generation application.**

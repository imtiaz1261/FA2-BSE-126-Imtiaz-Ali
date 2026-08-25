# 🎙️ AI Text-to-Speech

A professional Streamlit Text-to-Speech application using **Python 3.11+**, **Streamlit**, and **pyttsx3**.

The application converts typed or pasted text into a WAV audio file using the local operating-system speech engine.

## Features

- Large text input
- 5,000-character validation limit
- Character and word counter
- Generate Speech button
- Integrated audio player
- WAV audio download
- Installed voice selection
- Speech speed/rate control
- Volume control
- Clear text button
- User-friendly error handling
- Modular TTS service
- Offline/local TTS with pyttsx3
- No API key required

## Project structure

```text
text_to_speech/
│
├── app.py
├── services/
│   ├── __init__.py
│   └── tts_service.py
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

- Python 3.11 or newer
- Windows/macOS/Linux
- A system TTS voice/speech engine

## Windows installation

Open PowerShell inside the project folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run:

```powershell
streamlit run app.py
```

Open the URL shown by Streamlit, normally:

```text
http://localhost:8501
```

## macOS/Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Depending on the operating system, pyttsx3 may require a system speech engine. For example, Linux systems commonly need `espeak-ng` installed separately.

## How it works

```text
User enters text
       ↓
Streamlit validates input
       ↓
Voice / speed / volume selected
       ↓
TTSService
       ↓
pyttsx3 local speech engine
       ↓
WAV file
       ↓
Streamlit audio player
       ↓
Download
```

## Adding another TTS provider

TTS logic is isolated in:

```text
services/tts_service.py
```

You can later add providers such as gTTS or another cloud TTS API without putting provider-specific logic into `app.py`.

## Important note about Play/Stop

`st.audio()` provides browser-native playback controls. The exact play/pause/seek/volume controls depend on the browser. The application therefore generates a standard WAV file and lets the browser handle playback.

## Troubleshooting

### `No module named pyttsx3`

Run:

```powershell
pip install pyttsx3
```

### Windows voices are missing

Check Windows speech settings and ensure at least one speech voice is installed.

### `pywin32` problem on Windows

Run:

```powershell
pip install --upgrade pywin32
```

Then retry:

```powershell
streamlit run app.py
```

### Audio file is not generated

Make sure a local TTS voice is installed and test the Windows speech engine with another application first.

## Security/privacy

This version uses local pyttsx3 processing. The entered text is not intentionally sent to an external TTS service.

Do not add API keys to source code. If you later add a cloud provider, keep credentials in `.env` and load them with environment variables.

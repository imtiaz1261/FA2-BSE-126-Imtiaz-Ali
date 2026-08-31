# 🎙️ VoiceForge AI — Offline Text-to-Speech

**VoiceForge AI** is a professional and user-friendly Streamlit-based Text-to-Speech application built with **Python 3.11+**, **Streamlit**, and **pyttsx3**.

The application converts typed or pasted text into a high-quality **WAV audio file** using the local operating-system speech engine. It works offline and does not require an API key or external cloud service.

## ✨ Features

* 📝 Large text input area
* 🔢 5,000-character validation limit
* 📊 Character and word counter
* 🎙️ Generate Speech button
* 🔊 Integrated audio player
* 💾 WAV audio download
* 🗣️ Installed system voice selection
* ⚡ Speech speed/rate control
* 🔉 Volume control
* 🧹 Clear text button
* ⚠️ User-friendly error handling
* 🧩 Modular TTS service architecture
* 🔒 Offline/local speech processing
* 🔑 No API key required

## 📁 Project Structure

```text
voiceforge_ai/
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

## ⚙️ Requirements

* Python 3.11 or newer
* Windows / macOS / Linux
* A system TTS voice/speech engine
* Streamlit
* pyttsx3

## 🪟 Windows Installation

Open PowerShell inside the project folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the application:

```powershell
streamlit run app.py
```

Open the URL shown by Streamlit, normally:

```text
http://localhost:8501
```

## 🍎 macOS / 🐧 Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Depending on the operating system, **pyttsx3** may require a system speech engine. For example, Linux systems commonly require `espeak-ng` to be installed separately.

## 🔄 How It Works

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
WAV audio file
       ↓
Streamlit audio player
       ↓
Download audio
```

## 🧩 Modular TTS Architecture

The core speech-generation logic is separated from the Streamlit interface and is located in:

```text
services/tts_service.py
```

This makes the application easier to maintain and extend.

Additional TTS providers such as **gTTS** or cloud-based speech APIs can be added later without placing provider-specific logic directly inside `app.py`.

## ▶️ Play / Stop Controls

`st.audio()` provides browser-native audio playback controls.

The exact play, pause, seek, and volume controls may vary depending on the browser being used. The application therefore generates a standard **WAV audio file**, allowing the browser to handle playback.

## 🛠️ Troubleshooting

### `No module named pyttsx3`

Install pyttsx3:

```powershell
pip install pyttsx3
```

### Windows Voices Are Missing

Check your Windows speech settings and make sure at least one compatible speech voice is installed.

### `pywin32` Problem on Windows

Run:

```powershell
pip install --upgrade pywin32
```

Then restart the application:

```powershell
streamlit run app.py
```

### Audio File Is Not Generated

Make sure a local TTS voice/speech engine is installed and working. You can test the Windows speech engine with another application before running VoiceForge AI again.

## 🔒 Security & Privacy

VoiceForge AI uses **local pyttsx3 processing** for speech generation.

The text entered into the application is not intentionally sent to an external TTS service.

No API key is required for the current version.

If a cloud-based provider is added in the future, credentials should be stored securely using environment variables rather than being placed directly in the source code.

## 🚀 Future Improvements

Possible future enhancements include:

* Multiple TTS provider support
* MP3 export
* Additional voice customization
* Voice preview
* Audio history
* Cloud TTS integration
* More advanced speech controls
* AI-powered voice styles
* Multi-language support

## 📌 Project Summary

**VoiceForge AI** provides a simple, professional, and privacy-friendly way to convert text into speech directly on your computer. By using Streamlit for the interface and pyttsx3 for local speech generation, the application remains lightweight, easy to use, and independent of external APIs.

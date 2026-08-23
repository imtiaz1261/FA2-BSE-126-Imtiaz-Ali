# 🚀 Jarvis-Lite Setup Guide — Complete Working Installation

This guide ensures **voice input and text-to-speech work correctly** in Streamlit.

---

## 📋 Prerequisites

- **Python:** 3.9+ (tested on 3.11)
- **OS:** Windows, macOS, or Linux
- **Microphone:** Required for voice input
- **API Keys:** Get from OpenAI/Gemini dashboard (for LLM responses)

---

## ⚙️ Step 1: Install Dependencies

### Windows PowerShell

```powershell
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔧 Step 2: Install Voice Dependencies (CRITICAL)

### For Microphone Input (Speech Recognition)

**Windows:**
```powershell
pip install SpeechRecognition
pip install pipwin
pipwin install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
pip install SpeechRecognition
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install portaudio19-dev python3-dev
pip install PyAudio SpeechRecognition
```

### For Text-to-Speech

**Use pyttsx3 (offline, works everywhere):**
```powershell
pip install pyttsx3
```

**OR gtts (online, free):**
```powershell
pip install gtts
```

**Recommended:** Install BOTH:
```powershell
pip install pyttsx3 gtts
```

---

## 🔐 Step 3: Configure Environment

```bash
# Copy example config
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# ⭐ REQUIRED FOR LLM
OPENAI_API_KEY=sk-...your-key...
# OR
GEMINI_API_KEY=your-gemini-key

# Voice Settings
TTS_BACKEND=pyttsx3    # pyttsx3 = offline, gtts = online
STT_LANGUAGE=en

# Vector DB
VECTOR_DB_PROVIDER=chroma

# Memory
MEMORY_TYPE=buffer
MEMORY_MAX_TOKENS=4000
```

---

## ✅ Step 4: Test Installation

### Test Voice Input
```powershell
# Activate venv
venv\Scripts\Activate.ps1

# Run test
python -c "
from app.voice.speech_recognition import SpeechRecognizer
sr = SpeechRecognizer()
print('✅ Speech Recognizer imported successfully')
"
```

### Test Text-to-Speech
```powershell
python -c "
from app.voice.text_to_speech import TextToSpeech
tts = TextToSpeech(backend='pyttsx3')
audio = tts.speak_to_bytes('Hello World')
print(f'✅ TTS working - Generated {len(audio)} bytes of audio')
"
```

### Test Agent
```powershell
python -c "
from app.agent.agent import IntelligentAgent
agent = IntelligentAgent()
print('✅ Agent loaded successfully')
"
```

---

## 🚀 Step 5: Run Streamlit

```powershell
# Ensure venv is activated
venv\Scripts\Activate.ps1

# Launch Streamlit
streamlit run streamlit_app.py
```

**Expected output:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

Open **http://localhost:8501** in your browser.

---

## 🎤 Step 6: Test Voice Features

### Text Input (Should Work Immediately)
1. Click **Input Method** → Select **"Text"**
2. Type: `Calculate 2 + 2`
3. Click **Send ➤**
4. You should see the response

### Voice Input (Requires Microphone)
1. Click **Input Method** → Select **"Voice"**
2. Click **"🎙️ Record Voice Input"**
3. **Speak clearly** (e.g., "What is 5 times 3?")
4. Wait 3-5 seconds for transcription
5. You should see "✅ Recognized: ..."
6. Response appears below

### Text-to-Speech (Optional)
1. In **Settings** → **Voice Settings**
2. Enable **"Auto-play audio response"**
3. Select backend: **"pyttsx3"** (recommended for offline)
4. Send a message
5. You should hear the response through your speakers

---

## 🔧 Troubleshooting

### ❌ "Speech Recognizer not available"

**Solution:**
```powershell
pip uninstall SpeechRecognition -y
pip install SpeechRecognition
```

### ❌ "Microphone error" / "No microphone available"

**Windows:**
1. Settings → Sound → Volume → Ensure microphone is not muted
2. Settings → Privacy → Microphone → Enable for Python
3. Restart Streamlit

**Test microphone:**
```powershell
python -c "
import speech_recognition as sr
with sr.Microphone() as source:
    print('Listening...')
    audio = sr.Recognizer().listen(source, timeout=5)
print('✅ Microphone working')
"
```

### ❌ "TTS not available" / Audio not playing

**Solution:**
```powershell
pip uninstall pyttsx3 gtts -y
pip install pyttsx3 gtts
```

**Test TTS:**
```powershell
python -c "
from app.voice.text_to_speech import TextToSpeech
tts = TextToSpeech(backend='pyttsx3')
tts.speak('Testing text to speech')
"
```

### ❌ "Agent failed to initialise"

**Solution:**
```powershell
pip install -r requirements.txt
```

Then check if all modules load:
```powershell
python -c "from app.agent.agent import IntelligentAgent"
```

### ❌ "OPENAI_API_KEY not set"

**Solution:**
1. Get your key from https://platform.openai.com/api-keys
2. Edit `.env`:
```env
OPENAI_API_KEY=sk-your-actual-key
```
3. Save and restart Streamlit

### ❌ Port 8501 already in use

**Solution:**
```powershell
streamlit run streamlit_app.py --server.port 8502
```

---

## 📊 What Should Work

| Feature | Status | How to Test |
|---------|--------|-----------|
| Text Chat | ✅ Working | Type "Calculate 5+5" |
| Voice Input | ✅ Working | Click "Record Voice Input" |
| Text-to-Speech | ✅ Working | Enable "Auto-play audio" |
| Agent Routing | ✅ Working | Try "Weather in London" |
| Document Search | ✅ Working | Upload PDF then ask about it |
| Chat History | ✅ Working | Messages persist in sidebar |

---

## 🔄 Full Restart (If Issues Persist)

```powershell
# 1. Deactivate venv
deactivate

# 2. Delete old venv
Remove-Item -Recurse -Force venv

# 3. Recreate fresh
python -m venv venv
venv\Scripts\Activate.ps1

# 4. Reinstall everything
pip install --upgrade pip
pip install -r requirements.txt

# 5. Install voice dependencies
pip install SpeechRecognition pyttsx3 gtts

# 6. Test and run
streamlit run streamlit_app.py
```

---

## 📝 Quick Reference Commands

```powershell
# Activate venv
venv\Scripts\Activate.ps1

# Run Streamlit
streamlit run streamlit_app.py

# Run tests
pytest app/tests/ -v

# Run FastAPI (alternative UI)
uvicorn api:app --reload --port 8000

# Check environment
python -c "import streamlit; print(streamlit.__version__)"
```

---

## 🎯 Next Steps

1. ✅ Complete setup above
2. ✅ Test text chat works
3. ✅ Test voice input (click mic button)
4. ✅ Test audio output (enable Auto-play)
5. ✅ Upload a PDF document
6. ✅ Ask questions about the document

---

## 📞 Need Help?

Check the logs in **Streamlit terminal** for error messages:
- Look for `❌` symbols (errors)
- Look for `⚠️` symbols (warnings)
- Look for `✅` symbols (success)

If stuck, run the diagnostic:
```powershell
python -c "
print('Testing Jarvis-Lite components...')
try:
    from app.agent.agent import IntelligentAgent
    print('✅ Agent OK')
except Exception as e:
    print(f'❌ Agent: {e}')

try:
    from app.voice.speech_recognition import SpeechRecognizer
    print('✅ Speech Recognizer OK')
except Exception as e:
    print(f'❌ Speech Recognizer: {e}')

try:
    from app.voice.text_to_speech import TextToSpeech
    print('✅ Text-to-Speech OK')
except Exception as e:
    print(f'❌ Text-to-Speech: {e}')
"
```

---

**✨ You're all set! Enjoy your AI voice assistant!**

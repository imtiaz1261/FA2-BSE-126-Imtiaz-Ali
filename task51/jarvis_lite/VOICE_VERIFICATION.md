# ✅ Voice Features Verification Checklist

Follow this checklist to confirm all voice features are working correctly.

---

## Step 1: Verify Dependencies ✅

Run this command in PowerShell (from the project directory):

```powershell
cd "c:\Users\IJAZ AHMAD\Desktop\Internship Work\week5\task51\jarvis_lite"
venv\Scripts\Activate.ps1
pip list | Select-String "pyttsx3|PyAudio|gtts|SpeechRecognition"
```

**Expected Output:**
```
gTTS                                     2.5.4
PyAudio                                  0.2.14
pyttsx3                                  2.99
SpeechRecognition                        3.10.x
```

✅ **PASS** - All four packages show up  
❌ **FAIL** - Any missing? Run: `pip install -r requirements.txt`

---

## Step 2: Open Streamlit App ✅

Open browser: **http://localhost:8501**

### What You Should See:
```
🤖 Jarvis-Lite
   Chat | Voice I/O | RAG

📝 Chat History
   [System: Hello! I'm Jarvis...]

💬 Chat Input Box
   [Type your question here...]

🎤 Listen (Voice Input)        [Button]
🔊 Enable Auto-play Audio       [Toggle]
📁 Upload Documents              [File Uploader]
```

✅ **PASS** - All UI elements visible  
❌ **FAIL** - Blank page? Check console (F12) for errors

---

## Step 3: Test Text Chat ✅

1. Type in chat: `"Hello, how are you?"`
2. Click **Send** or press Enter
3. Wait for response (3-5 seconds)

**Expected:** Response from Jarvis appears in chat history

✅ **PASS** - Jarvis responds with text  
❌ **FAIL** - No response? Check terminal for errors

---

## Step 4: Test Voice Input ✅

1. Click **🎤 Listen (Voice Input)** button
2. Speak clearly: `"What is the weather in London?"`
3. Wait 2-3 seconds for processing
4. Check that text appears as user message

**Expected:** Your speech converts to text, question is sent automatically

✅ **PASS** - Voice input recognized and sent  
❌ **FAIL** - Error message? See Troubleshooting below

---

## Step 5: Test Voice Output ✅

1. Toggle **Enable Auto-play Audio** ON
2. Type or say: `"Introduce yourself"`
3. Wait for response
4. Listen for audio playback

**Expected:** After Jarvis responds, you hear audio speaking the response

✅ **PASS** - Audio plays automatically  
❌ **FAIL** - No audio? See Troubleshooting below

---

## Step 6: Test Error Handling ✅

### Test Missing Microphone Error
1. Disconnect microphone (if possible)
2. Click **🎤 Listen** button
3. Check error message

**Expected:** Clear error like:
```
❌ Microphone Error
   Could not find microphone. Please check:
   - Microphone is connected
   - Run: python -m pip install --upgrade PyAudio
```

✅ **PASS** - Error message is clear  
❌ **FAIL** - Generic error? Report this

---

## Step 7: Test RAG (Document Upload) ✅

1. Click **📁 Upload Documents**
2. Select a PDF file (or .docx/.txt)
3. Wait for upload confirmation
4. Ask a question about the document: `"What is the main topic?"`
5. Jarvis should answer based on document content

**Expected:** Jarvis retrieves info from uploaded document

✅ **PASS** - RAG working with uploaded documents  
❌ **FAIL** - Error during upload? Check file format and size

---

## Terminal Log Verification ✅

Check the terminal running Streamlit for these success markers:

```
✅ Agent loaded successfully
✅ TTS loaded successfully (pyttsx3)
✅ SR loaded successfully
✅ Query processed: [your question]
```

### You Should NOT See:
```
❌ WARNING: No TTS backend available
❌ ERROR: Agent loading failed
❌ ❌ SR loading failed
```

---

## Troubleshooting Guide

### ❌ "No microphone detected"

**Symptoms:** Error appears when clicking voice input button

**Solution:**
```powershell
# 1. Test microphone availability:
python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_device_count(), 'devices found')"

# 2. List available microphones:
python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_indexes())"

# 3. If no devices found, check Windows:
#    Settings → Sound → Advanced → Volume mixer
```

---

### ❌ "No TTS backend available"

**Symptoms:** Voice output doesn't work, no audio plays

**Solution:**
```powershell
# 1. Verify installations:
pip list | Select-String "pyttsx3|gtts"

# 2. If missing, reinstall:
pip install pyttsx3 gtts

# 3. Restart Streamlit:
# Press Ctrl+C in terminal
# Run: streamlit run streamlit_app.py --server.port 8501
```

---

### ❌ "Auto-play audio not working"

**Symptoms:** Toggle enabled but no audio plays

**Solution:**
1. Browser Settings: Allow audio autoplay
   - Chrome: Settings → Privacy & Security → Site Settings → Autoplay → Allow audio
   - Firefox: Preferences → Permissions → Autoplay → Allow Audio
   - Edge: Settings → Cookies & Site Permissions → Autoplay → Allow

2. Check browser console (F12 → Console tab) for errors

3. Try manual playback: Click the audio player that appears

---

### ❌ "Streamlit won't start"

**Symptoms:** Terminal shows error, app won't load

**Solution:**
```powershell
# 1. Kill existing Streamlit process:
Get-Process streamlit | Stop-Process -Force

# 2. Check Python environment:
python --version  # Should be 3.9+

# 3. Verify venv is activated:
# You should see (venv) in terminal prefix

# 4. Reinstall dependencies:
pip install -r requirements.txt --force-reinstall

# 5. Start fresh:
streamlit run streamlit_app.py --server.port 8501
```

---

## Performance Notes

| Operation | Expected Time |
|-----------|---------------|
| App startup | 3-5 seconds |
| Text query response | 2-5 seconds |
| Voice input (speech-to-text) | 2-3 seconds |
| Text-to-speech generation | 1-3 seconds |
| Audio playback | Real-time |
| Document upload (PDF) | Depends on size (1-10 MB) |

---

## Success Criteria ✅

All items should be checked:
- [ ] Dependencies installed (Step 1)
- [ ] Streamlit app loads (Step 2)
- [ ] Text chat works (Step 3)
- [ ] Voice input recognized (Step 4)
- [ ] Audio plays automatically (Step 5)
- [ ] Error messages are clear (Step 6)
- [ ] Document upload works (Step 7)
- [ ] Terminal shows success markers (Terminal verification)

**If all ✅ checked:** Voice I/O is fully functional!

---

## Final Checklist

Before declaring "DONE":

```
[ ] Microphone test: Can speak and hear yourself?
[ ] Speaker test: Can hear audio output?
[ ] Internet: Required for gtts (text-to-speech), optional for pyttsx3
[ ] Permissions: Microphone access granted to browser?
[ ] Browser: Autoplay audio enabled in settings?
```

---

**Contact:** If issues persist, check logs in terminal or open GitHub issue.

*Verification Guide - Updated 2026-08-06*

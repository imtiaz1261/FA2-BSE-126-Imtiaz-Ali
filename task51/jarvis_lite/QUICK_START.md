# 🚀 Quick Start - Jarvis-Lite Voice Chat

## ⚡ One Command to Start

```powershell
cd "c:\Users\IJAZ AHMAD\Desktop\Internship Work\week5\task51\jarvis_lite"
venv\Scripts\Activate.ps1
streamlit run streamlit_app.py --server.port 8501
```

Then open your browser: **http://localhost:8501**

---

## 📖 What to Do

### ✅ Text Chat
1. Type your question
2. Press Enter
3. Get response

### ✅ Voice Input (Speak to Jarvis)
1. Click **🎤 Listen** button
2. Speak your question
3. Wait 2-3 seconds
4. Question sent automatically

### ✅ Voice Output (Hear Response)
1. Toggle **Enable Auto-play Audio** in sidebar
2. Chat normally (text or voice)
3. Hear Jarvis respond

### ✅ Ask About Documents (RAG)
1. Click **📁 Upload Documents**
2. Select PDF, DOCX, or TXT file
3. Ask: "What's in the document?"
4. Get answers from your document

---

## 🔧 If Something Breaks

### ❌ No microphone detected
```powershell
# Test: python -c "import pyaudio; print('PyAudio OK')"
```

### ❌ No audio output
- Open **Settings** → **Autoplay** → Enable audio

### ❌ App won't start
```powershell
Get-Process streamlit | Stop-Process -Force
streamlit run streamlit_app.py --server.port 8501
```

---

## 📚 Full Docs

- **VOICE_FIX_COMPLETE.md** - What was fixed and how
- **VOICE_VERIFICATION.md** - Complete verification checklist
- **FIX_SUMMARY.txt** - Technical details
- **SETUP_GUIDE.md** - Installation troubleshooting
- **README.md** - Full project overview

---

## 💡 Tips

1. **Speak clearly** - Best results with clear pronunciation
2. **Use English** - Works best with English speech
3. **Check volume** - Ensure speakers are on
4. **Stable internet** - Needed for some features
5. **Microphone enabled** - Check Windows sound settings

---

## 📞 Troubleshooting

Check **VOICE_VERIFICATION.md** for detailed troubleshooting of:
- Microphone issues
- Audio playback problems
- App startup errors
- Document upload issues

---

## ✨ Ready!

Your Jarvis-Lite is ready to use at **http://localhost:8501**

**Enjoy chatting! 🎉**

---

*Last updated: 2026-08-06*

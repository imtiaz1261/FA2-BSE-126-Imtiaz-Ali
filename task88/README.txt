GROQ Story / Poem Generator

1. Install Python 3.9+.
2. Open Command Prompt/PowerShell in this folder.
3. Install the Groq SDK:
   pip install -r requirements.txt

4. Set your Groq API key.

Windows CMD:
   set GROQ_API_KEY=YOUR_GROQ_API_KEY

Windows PowerShell:
   $env:GROQ_API_KEY="YOUR_GROQ_API_KEY"

macOS/Linux:
   export GROQ_API_KEY="YOUR_GROQ_API_KEY"

5. Run:
   python app.py

The program asks for:
- Theme/topic (e.g. friendship, monsoon)
- Story or poem
- Style: funny, emotional, or adventure

It uses Groq's OpenAI GPT-OSS 20B model.

Security:
Do not hard-code your API key into app.py or upload it to GitHub.

# Natural Language To-Do App (Groq LLM)

User **natural language** mein command deta hai (jaise *"kal 5 baje
doctor appointment add karo"*), aur LLM (Groq — `llama-3.3-70b-versatile`)
usay **structured task** (`title`, `date`, `time`) mein convert karke
ek list mein save karta hai. Tasks `tasks.json` file mein persist hote
hain, taake app dobara chalane par bhi purani list mile.

## Project Structure
```
todo_app/
├── main.py             # Main app loop (natural language -> LLM -> structured task -> save)
├── requirements.txt     # Python dependencies
├── .env.example         # Sample env file (copy this to .env)
├── .gitignore           # Ensures .env and tasks.json never get committed
└── README.md            # Yeh file
```

## Setup Instructions

### 1. Project extract karein
```bash
unzip todo_app.zip
cd todo_app
```

### 2. (Optional) Virtual environment banayein
```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
```

### 3. Dependencies install karein
```bash
pip install -r requirements.txt
```

### 4. Apni Groq API key set karein
```bash
cp .env.example .env
```
`.env` file open karke apni asal Groq API key daalein:
```
GROQ_API_KEY=gsk_your_real_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

**Zaroori:** `.env` ko kabhi git mein commit na karein (already
`.gitignore` mein hai).

### 5. App run karein
```bash
python main.py
```

## Example Session
```
✅  Natural Language To-Do App

Commands:
  - Koi bhi natural language command likhein task add karne ke liye
    e.g. 'kal 5 baje doctor appointment add karo'
  - 'list'  -> saari tasks dekhein
  - 'exit'  -> app band karein

> kal 5 baje doctor appointment add karo
✅ Task add ho gayi: "Doctor appointment" — 2026-08-01 at 17:00

> parso subah 9 baje meeting with client add karo
✅ Task add ho gayi: "Meeting with client" — 2026-08-02 at 09:00

> list

=======================================================
 📋  YOUR TO-DO LIST
=======================================================
  1. [2026-08-01 at 17:00] Doctor appointment
  2. [2026-08-02 at 09:00] Meeting with client
=======================================================

> exit
Task list save ho chuki hai. Allah Hafiz! 👋
```

## Notes
- App aaj ki tareekh khud detect karta hai (system date se) taake
  "kal", "parso", "agle hafte" jaisi relative dates sahi tarah resolve
  ho sakein.
- Agar time na diya jaye (e.g. "kal doctor appointment add karo"), to
  `time` field `null` save hogi.
- Tasks `tasks.json` file mein save hote hain — is file ko delete
  karne se list reset ho jayegi.
- Agar LLM output schema follow na kare (e.g. invalid date format),
  script clear error dikhayega aur task save nahi karega.
- `main.py` mein `TASK_PROMPT` ko edit karke date/time parsing rules
  ya title extraction style tweak kar sakte hain.

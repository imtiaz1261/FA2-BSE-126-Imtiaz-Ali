# AI Professional Cover Letter Generator

LLM-powered Python project that collects the user's name, skills,
experience, and target job role, then generates three tailored cover
letters: Formal, Friendly, and Concise.

## Setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Run:

```powershell
python app.py
```

The prompt instructs the LLM not to invent qualifications, companies,
achievements, certifications, or years of experience.

Do not commit `.env` to GitHub. If a real API key has been exposed,
rotate/revoke it and use a new key.

# 3-Line Paragraph Summarizer

Paste a paragraph, pick a summary length (short / medium / long), and
get back an exact 3-line summary — powered by Groq (free, fast).

## Structure
```
paragraph-summarizer/
├── app.py            # Streamlit UI
├── summarizer.py       # Core summarization logic (Groq call)
├── config.py            # Loads settings from .env
├── requirements.txt
├── .env                 # Your secret key (already filled in, gitignored)
├── .env.example
└── .gitignore
```

## Setup
```bash
pip install -r requirements.txt
```
Your `.env` already has a Groq key filled in and ready to go — no
extra setup needed. If you ever need a fresh key: https://console.groq.com/keys
(free, no credit card).

## Run
```bash
streamlit run app.py
```
Paste any paragraph, choose Short / Medium / Long, click **Summarize**.

## How the length option works
The summary is **always exactly 3 lines** — the length setting changes
how much detail each line carries, not the number of lines:
- **Short** — ~6-10 words/line, key words only
- **Medium** — ~12-18 words/line, full sentences (default)
- **Long** — ~20-30 words/line, more detail per sentence

## Error handling
- Empty paragraph → clear inline error, no API call made
- Missing/invalid API key → clear message pointing to the Groq console
- API request failure → caught and shown in the UI, app doesn't crash

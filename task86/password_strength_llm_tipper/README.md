# 🔐 Password Strength Checker + LLM Personalized Tip

Streamlit app that checks password strength locally using length, uppercase, number and symbol rules, then uses Groq to generate a personalized tip.

## Privacy
The actual password is NEVER sent to the LLM. Only aggregate results (score, length, failed rules) are sent.

## Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```
Set:
```env
GROQ_API_KEY=your_real_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

## Run
```powershell
streamlit run app.py
```

## Tests
```powershell
pytest -q
```

## Project
```text
password_strength_llm_tipper/
├── app.py
├── strength_checker.py
├── llm_tip.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── tests/test_strength_checker.py
```

For real authentication systems, use a password manager/long unique passphrases and established password hashing such as Argon2id. Never log or send plaintext passwords to an LLM.

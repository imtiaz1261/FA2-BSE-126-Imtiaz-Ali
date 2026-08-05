# URL Article Summarizer (BeautifulSoup + Groq LLM)

User se ek **URL** leta hai, uska text content **BeautifulSoup** se
fetch/extract karta hai, aur LLM (Groq — `llama-3.3-70b-versatile`) se
us article ka **5-line summary** generate karwa kar print karta hai.

## Project Structure
```
url_summarizer/
├── main.py             # Main script (fetch URL -> extract text -> LLM summary -> print)
├── requirements.txt     # Python dependencies
├── .env.example         # Sample env file (copy this to .env)
├── .gitignore           # Ensures .env never gets committed
└── README.md            # Yeh file
```

## Setup Instructions

### 1. Project extract karein
```bash
unzip url_summarizer.zip
cd url_summarizer
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

### 5. Script run karein
```bash
python main.py
```
Jab prompt aaye, koi bhi article ka URL paste kar dein.

## Example Session
```
📰  URL Article Summarizer

Article ka URL daalein: https://example.com/some-article

⏳ Page fetch aur parse ho raha hai...
⏳ LLM se 5-line summary generate ho raha hai...

============================================================
 ✅  5-LINE SUMMARY
============================================================
The article discusses recent advancements in renewable energy...
Researchers found that solar efficiency improved by 15% this year...
Government policies are shifting to support faster adoption...
Experts warn that infrastructure investment must scale accordingly...
Overall, the outlook for clean energy remains positive for 2026.
============================================================
```

## Notes
- Script pehle `<article>` tag dhoondhta hai; agar na mile to poore
  `<body>` se paragraph (`<p>`, `<h1>`, `<h2>`, `<h3>`, `<li>`) tags ka
  text extract karta hai.
- Bohot lambe articles ko safety ke liye ~12,000 characters tak
  truncate kiya jata hai LLM ko bhejne se pehle (`MAX_CHARS_TO_LLM` variable
  `main.py` mein change kar sakte hain).
- Agar page JavaScript-heavy ho (content baad mein render hota ho), to
  BeautifulSoup ko kam text milega — is case mein script warning dikhayegi.
  Aise pages ke liye Selenium/Playwright jaisay browser-based scraper ki
  zaroorat hogi (yeh project simple static-HTML fetching tak mehdood hai).
- `SUMMARY_PROMPT` ko `main.py` mein edit karke summary ka tone, length,
  ya language (e.g. Urdu summary) tweak kar sakte hain.

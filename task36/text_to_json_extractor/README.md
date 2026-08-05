# Unstructured Text → Structured JSON Extractor

Yeh Python project kisi bhi **unstructured text** (jaise resume ya product
description) ko LLM (Groq — `llama-3.3-70b-versatile`) prompt ke through
**structured JSON** mein convert karta hai:

- **Resume** → `{ name, skills, experience }`
- **Product description** → `{ name, price, features }`

Output ko **Pydantic** ke zariye validate kiya jata hai — agar LLM ka
output schema follow nahi karta, to clearly error dikhaya jata hai; agar
valid ho to neatly formatted JSON print hota hai.

## Project Structure
```
text_to_json_extractor/
├── main.py             # Main script (sample inputs + LLM extraction + validation + print)
├── requirements.txt     # Python dependencies
├── .env.example         # Sample env file (copy this to .env)
├── .gitignore           # Ensures .env never gets committed
└── README.md            # Yeh file
```

## Setup Instructions

### 1. Project extract karein
```bash
unzip text_to_json_extractor.zip
cd text_to_json_extractor
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

**Zaroori:** `.env` ko kabhi git mein commit na karein (already `.gitignore`
mein hai). Agar key kahin publicly share ho chuki ho, Groq console
(https://console.groq.com) se turant regenerate kar dein.

### 5. Project run karein
```bash
python main.py
```

## Output (example)
```
======================================================================
INPUT TYPE: resume
RAW TEXT: Ayesha Khan is a Software Engineer with 4 years of experience...
----------------------------------------------------------------------
✅ Valid structured output:

{
  "name": "Ayesha Khan",
  "skills": ["Python", "JavaScript", "React", "PostgreSQL"],
  "experience": "4 years of experience building web applications, including leading a team of 3 developers."
}
```

Agar LLM ka output schema break kare (e.g. missing field, wrong type),
script `❌ Validation failed` dikhayega, raw LLM output print karega, aur
exact validation error batayega — taake aap prompt ya schema adjust kar
sakein.

## Customizing
- `main.py` mein `SAMPLE_INPUTS` list ko edit karke apna khud ka resume /
  product description text daal sakte hain (`type` ko `"resume"` ya
  `"product"` set karein).
- Naya document type add karna ho (e.g. invoice), to:
  1. Ek naya Pydantic schema class banayein (jaise `InvoiceSchema`).
  2. `SCHEMA_MAP` aur `PROMPT_MAP` mein add karein.
  3. Us type ke liye ek naya prompt template likhein.

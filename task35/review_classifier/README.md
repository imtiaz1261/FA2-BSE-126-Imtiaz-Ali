# Customer Review Sentiment Classifier (Groq / Llama 3.3 70B)

Yeh chota sa Python project 5-10 sample customer reviews ko ek **LLM prompt**
(Groq API — `llama-3.3-70b-versatile`) ke zariye **Positive, Negative, ya
Neutral** classify karta hai aur result ko table format mein terminal par
print karta hai.

## Project Structure
```
review_classifier/
├── main.py             # Main script (reviews + LLM classification + table print)
├── requirements.txt     # Python dependencies
├── .env.example         # Sample env file (copy this to .env)
├── .gitignore           # Ensures .env never gets committed
└── README.md            # Yeh file
```

## Setup Instructions

### 1. Project extract karein
```bash
unzip review_classifier.zip
cd review_classifier
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
`.env.example` ko copy karke `.env` banayein:
```bash
cp .env.example .env
```
Phir `.env` file open karke apni asal Groq API key daalein:
```
GROQ_API_KEY=gsk_your_real_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

**Zaroori:** `.env` file ko kabhi bhi git mein commit na karein — yeh
`.gitignore` mein already add hai. Agar aapki key kahin publicly share ho
chuki hai (jaise chat, GitHub, ya screenshot mein), to Groq console
(https://console.groq.com) se turant usay regenerate/rotate kar dein.

### 5. Project run karein
```bash
python main.py
```

## Output
Script har review ko Groq LLM ke prompt ke through classify karega aur
end mein aik neat table print karega:

```
+-----+------------------------------------------------------------+-----------+
|   # | Customer Review                                             | Sentiment |
+=====+==============================================================+===========+
|   1 | The product quality is amazing, and it arrived early...     | Positive  |
|   2 | Worst purchase I've made this year. It broke within...      | Negative  |
|   3 | It's okay, does the job but nothing special about it.       | Neutral   |
+-----+------------------------------------------------------------+-----------+
```

## Customizing
- `main.py` ke andar `SAMPLE_REVIEWS` list ko edit karke apne khud ke
  reviews add ya replace kar sakte hain.
- `CLASSIFICATION_PROMPT` ko edit karke prompt wording tweak kar sakte hain.
- `.env` mein `GROQ_MODEL` change karke Groq ka koi aur available model
  (e.g. `llama-3.1-8b-instant`) bhi use kar sakte hain.

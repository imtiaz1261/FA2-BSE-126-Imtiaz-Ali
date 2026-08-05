# MCQ Generator (Groq LLM)

User se ek **paragraph ya topic** leta hai, LLM (Groq — `llama-3.3-70b-versatile`)
se us par **5 multiple-choice questions** generate karwata hai (har
question ke 4 options + ek correct answer), output ko **Pydantic** se
validate karta hai, aur clean, readable format mein terminal par print
karta hai.

## Project Structure
```
mcq_generator/
├── main.py             # Main script (input + LLM MCQ generation + validation + print)
├── requirements.txt     # Python dependencies
├── .env.example         # Sample env file (copy this to .env)
├── .gitignore           # Ensures .env never gets committed
└── README.md            # Yeh file
```

## Setup Instructions

### 1. Project extract karein
```bash
unzip mcq_generator.zip
cd mcq_generator
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

### 5. Project run karein
```bash
python main.py
```
Jab prompt aaye, apna paragraph/topic type kar dein — ya sirf Enter
dabayein taake built-in sample (Photosynthesis) topic use ho jaye.

## Example Output
```
📚  MCQ Generator

Your paragraph/topic: [Enter dabaya - sample topic use hui]

⏳ Generating 5 MCQs, please wait...

=================================================================
 📝  GENERATED QUIZ (5 Multiple Choice Questions)
=================================================================

Q1. What is the main pigment used in photosynthesis to absorb sunlight?
   A) Carotene
   B) Chlorophyll
   C) Xanthophyll
   D) Anthocyanin
   ✅ Correct Answer: B) Chlorophyll

Q2. Which gas is released as a byproduct of photosynthesis?
   A) Carbon Dioxide
   B) Nitrogen
   C) Oxygen
   D) Hydrogen
   ✅ Correct Answer: C) Oxygen
...
=================================================================
```

## Notes
- Agar LLM ka output schema follow na kare (e.g. 4 se kam/zyada options,
  ya 5 se kam/zyada questions), script `❌ Output validation fail hui`
  dikhayega, raw LLM output print karega, aur exact validation error
  batayega.
- `main.py` mein `MCQ_PROMPT` ko edit karke difficulty level, question
  style, ya language (e.g. Urdu MCQs) tweak kar sakte hain.
- Question count (5) ya options count (4) change karna ho to
  `MCQ_PROMPT` aur `MCQSet`/`MCQ` ke Pydantic validators dono update
  karne honge.

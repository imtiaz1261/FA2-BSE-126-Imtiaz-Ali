# FAQ Bot — difflib Matching + LLM Fallback

Stores 10 question-answer pairs in a text file. When you ask a question,
it finds the best-matching FAQ using `difflib` similarity matching; if
nothing matches well enough, it asks the LLM for a generic answer instead.

## Files

| File            | Purpose                                   |
|------------------|----------------------------------------------|
| `faqs.txt`      | 10 Q&A pairs, in `Q:`/`A:` format          |
| `faq_bot.py`    | Main script — run this                    |
| `requirements.txt` | Dependencies                          |
| `secret_key.py` | Your Groq API key (never commit this)    |
| `.gitignore`    | Excludes `secret_key.py`                   |

## Setup

```
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

**Interactive:**
```
python faq_bot.py
```

**Single question:**
```
python faq_bot.py --question "How do I reset my password?"
```

## How matching works

1. **Keyword extraction**: both the user's question and every FAQ
   question have common stopwords removed ("what", "how", "can", "the",
   etc.), leaving just the meaningful words.
2. **Similarity scoring**: `difflib.SequenceMatcher` compares the
   remaining keywords and produces a 0.0-1.0 similarity score.
3. **Threshold**: if the best score is below `SIMILARITY_THRESHOLD`
   (0.45), no FAQ is considered a good enough match, and the question
   goes to the LLM instead.

## An honest limitation, found through testing

`difflib` compares **characters/keywords**, not **meaning** — it has no
concept of synonyms. This was tested directly and found real:

- Works: "How do I reset my password?" matches the password FAQ (score 1.00)
- Works: "Do you have student discounts?" matches the student FAQ (score 0.85)
- Limitation: "What time are you open?" does NOT match "business hours"
  (score only 0.43) — different words, same meaning, but difflib can't
  tell that "time/open" and "business/hours" mean the same thing.

**Why this is the safer tradeoff, not a bug to "fix" by lowering the
threshold:** lowering the threshold to catch that specific paraphrase
was tested and found to let in a worse problem — "Can I get my money
back?" started matching the password-reset FAQ (they happen to share a
few common characters), giving a completely wrong canned answer. A
missed match just costs one extra LLM call for a correct generic answer;
a wrong match gives a confidently incorrect answer. This project
deliberately favors the former.

If you need true synonym-aware matching (e.g. "time/open" correctly
matching "hours"), that requires semantic embeddings (like the
`sentence-transformers` approach used in earlier RAG projects), not
`difflib` — a good next step if this becomes a real limitation for you.

## Testing performed

Ran the real matching logic against the actual 10-FAQ file with 8+ test
queries, including deliberately re-testing after a fix: an early version
of the stopword-stripping logic caused a genuine wrong-topic match (a
refund question matching the password-reset FAQ), which was caught,
fixed, and re-verified — along with confirming the fix didn't break any
previously-working matches.

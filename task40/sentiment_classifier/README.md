# Customer Review Sentiment Classifier

Classifies customer reviews as **Positive**, **Negative**, or **Neutral**
using an LLM, and prints the results as a formatted table. Includes a
sample dataset of 10 reviews and a small test suite.

## Project structure

```
sentiment_classifier/
├── main.py                    Runs classification + prints results table
├── classifier.py               Core classification logic (reusable, testable)
├── config.py                   Loads settings from .env — no hardcoded secrets
├── data/
│   └── reviews.py              Sample dataset of 10 customer reviews
├── tests/
│   └── test_classifier.py      Unit tests with a mocked LLM client
├── .env.example                 Template for your local .env — fill this in
├── .gitignore                    Excludes .env, venv, caches
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Add your API key

```bash
# Windows
copy .env.example .env
# macOS/Linux
cp .env.example .env
```

Open `.env` and fill in:

```
GROQ_API_KEY=gsk_your_real_key_here
```

Get a free key (no credit card required) at:
https://console.groq.com/keys

> **Never commit your real `.env` file or share your API key in chats,
> docs, or screenshots.** `.env` is already excluded via `.gitignore` —
> only `.env.example` (with blanks) should ever be shared or committed.

## Run

```bash
python main.py
```

Example output:

```
Classifying 10 reviews (provider: groq, model: llama-3.1-8b-instant)...

+----+--------------------------------------------------------------+-------------+
|  # | Review                                                        | Sentiment   |
+====+================================================================+=============+
|  1 | The product arrived on time and works exactly as described...| Positive    |
|  2 | Terrible experience — the item broke after two days and su...| Negative    |
|  3 | It's okay, does the job but nothing special. Packaging was...| Neutral     |
|  4 | Absolutely love this! Best purchase I've made all year, hi...| Positive    |
|  5 | The quality is much lower than expected for the price. Qui...| Negative    |
+----+--------------------------------------------------------------+-------------+

Summary:
  Positive: 4
  Negative: 3
  Neutral: 3
```

(Table truncated here for readability — actual output includes all 10 rows.)

## Using your own reviews

Edit `data/reviews.py` and replace or extend the `SAMPLE_REVIEWS` list:

```python
SAMPLE_REVIEWS = [
    "Your review text here...",
    "Another review...",
]
```

## Design notes

- **`classify_review()` in `classifier.py`** uses a constrained system
  prompt so the model returns exactly one word (Positive/Negative/Neutral)
  — no explanations — keeping output reliable enough to parse.
- **`temperature=0`** is used for classification specifically, since
  deterministic output matters more than creativity here.
- **`_normalize_label()`** handles minor variations in the model's raw
  output (extra punctuation, different casing) instead of failing on
  something like `"positive."` — but still raises `ClassificationError`
  if the model returns something genuinely unrecognized, rather than
  silently guessing.
- **`classify_reviews()`** processes a full list and captures per-review
  errors individually, so one failed classification doesn't stop the
  whole batch — failed rows show `ERROR` in the table with details
  printed separately below it.
- **Table output** uses the `tabulate` library (`grid` format) for a
  clean, readable result — no manual string padding.

## Testing

```bash
pytest
```

Tests mock the LLM client entirely (`unittest.mock.MagicMock`), so the
suite runs instantly without a real API key or network call, and cover:

- correct classification parsing
- normalization of punctuation/casing variants
- empty-input validation
- unrecognized model output handling
- API failure wrapping
- batch classification with per-row error isolation

## Switching to OpenAI instead of Groq

Edit `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-real-openai-key
MODEL_NAME=gpt-4o-mini
```

## Troubleshooting

- **"GROQ_API_KEY is missing"** — `.env` wasn't created/filled in, or
  you're running from a different folder than the one containing it.
- **401 / authentication error** — key is wrong, expired, or revoked.
  Get a fresh one at https://console.groq.com/keys.
- **Rows show `ERROR`** — check the "Details on failed classifications"
  section printed below the table for the specific reason (often a rate
  limit or an unexpected model response).

## Possible extensions

- Load reviews from a CSV file instead of the hardcoded `data/reviews.py`.
- Export results to CSV/JSON alongside the printed table.
- Add confidence scores or short justifications per classification.
- Wrap this in a small Streamlit UI for non-technical users.

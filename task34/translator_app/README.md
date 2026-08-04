# Simple Translator App

A console-based translator: enter text and a target language (Hindi,
French, Spanish, or any other language), and get the LLM's translation
back. Built with a clean separation between the translation logic
(`translator.py`) and the CLI (`cli.py`), plus a small test suite.

## Project structure

```
translator_app/
├── cli.py                  Interactive command-line interface
├── translator.py           Core translation logic (reusable, testable)
├── config.py                Loads settings from .env — no hardcoded secrets
├── tests/
│   └── test_translator.py  Unit tests with a mocked LLM client
├── .env.example             Template for your local .env — fill this in
├── .gitignore                Excludes .env, venv, caches
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
python cli.py
```

Example session:

```
==================================================
  Simple Translator App
==================================================
Suggested languages: Hindi, French, Spanish, German, Arabic, Chinese, Japanese, Urdu, Portuguese, Russian
(You can also type any other language name.)
Type 'exit' at any prompt to quit.

Text to translate: Good morning, how are you?
Translate to (e.g. Hindi, French, Spanish): Hindi

Hindi translation:
सुप्रभात, आप कैसे हैं?

Text to translate: exit
Goodbye!
```

## Design notes

- **`translate()` in `translator.py`** uses a system prompt that instructs
  the model to return *only* the translated text — no quotes, no
  explanations — so the output is clean and predictable if you later
  want to pipe it into another program.
- **`temperature=0.3`** is used for translation requests specifically,
  since lower temperature gives more literal, consistent translations
  than the default creative-writing temperature.
- **Input validation** happens before any API call — empty text or empty
  target language raises `TranslationError` immediately rather than
  wasting a request.
- **`TranslationError`** wraps any underlying API failure (network,
  auth, rate limit) into one predictable exception type, so callers
  don't need to know about `openai` internals.
- **`SUPPORTED_LANGUAGES`** is a suggested list shown to the user, not a
  strict allow-list — the LLM can generally translate into other
  languages too if typed in.

## Testing

```bash
pytest
```

Tests mock the LLM client entirely (`unittest.mock.MagicMock`), so the
suite runs instantly without a real API key or network call, and
verifies:

- successful translation returns cleaned (stripped) text
- empty input text raises `TranslationError`
- empty target language raises `TranslationError`
- underlying API errors are wrapped into `TranslationError`

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
- **Translation looks off / includes extra text** — try a larger model
  (e.g. `llama-3.1-70b-versatile`) in `.env` for better translation
  quality on longer or more nuanced text.

## Possible extensions

- Add a `--text` / `--to` CLI flag mode (via `argparse`) for one-shot,
  non-interactive use in scripts.
- Add a Streamlit or FastAPI wrapper around `translate()` for a web UI.
- Cache repeated text+language pairs to avoid redundant API calls.

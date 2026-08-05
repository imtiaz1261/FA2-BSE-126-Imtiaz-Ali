# Grammar & Spelling Correction Tool

Paste a paragraph with grammar or spelling mistakes, and the tool
returns the corrected version along with a short list of what was
changed — powered by an LLM with a constrained JSON output format for
reliable parsing.

## Project structure

```
grammar_corrector/
├── cli.py                    Interactive command-line interface
├── corrector.py               Core correction logic (reusable, testable)
├── config.py                  Loads settings from .env — no hardcoded secrets
├── tests/
│   └── test_corrector.py      Unit tests with a mocked LLM client
├── .env.example                Template for your local .env — fill this in
├── .gitignore                   Excludes .env, venv, caches
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
=======================================================
  Grammar & Spelling Correction Tool
=======================================================
Paste your paragraph below. Type END on its own line when done
(or type 'exit' instead of pasting to quit):

She dont like going to the market because it always take too much time and she allways forget her list.
END

--- Corrected Text ---
She doesn't like going to the market because it always takes too much
time and she always forgets her list.

--- Changes Made ---
1. Fixed subject-verb agreement: "dont" to "doesn't"
2. Corrected spelling: "allways" to "always"
3. Fixed verb agreement: "take" to "takes"
4. Corrected spelling: "forget" to "forgets" for tense agreement
```

Type another paragraph to keep going, or type `exit` (instead of pasting
text) to quit.

## Design notes

- **Structured JSON output** — the system prompt in `corrector.py`
  forces the model to return `{"corrected_text": ..., "changes": [...]}`
  rather than free-form prose, so the corrected text and the change list
  can be reliably separated and displayed.
- **`_parse_response()`** tolerates the model occasionally wrapping its
  JSON in ` ```json ` code fences despite instructions not to — it
  strips those before parsing, but still raises `CorrectionError` on
  genuinely malformed output rather than guessing.
- **`temperature=0.2`** keeps corrections consistent and literal rather
  than creative rewrites — the goal is fixing mistakes, not changing
  style or voice.
- **Multi-line paste support** — `cli.py`'s `read_paragraph()` collects
  input line-by-line until you type `END`, so pasting a full paragraph
  (not just a single line) works naturally in the terminal.

## Testing

```bash
pytest
```

Tests mock the LLM client entirely (`unittest.mock.MagicMock`), so the
suite runs instantly without a real API key or network call, and cover:

- correct JSON parsing into corrected text + changes list
- empty-input validation
- API failure wrapping
- markdown code-fence stripping
- missing-field and invalid-JSON handling
- non-list `changes` values being coerced into a list

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
- **"Could not parse model response as JSON"** — rare, but can happen
  with weaker models on unusual input; try a larger model (e.g.
  `llama-3.1-70b-versatile`) in `.env` for more reliable structured output.

## Possible extensions

- Accept a `.txt` file path as input instead of only interactive paste.
- Highlight word-level diffs between original and corrected text.
- Add a `--tone` option (formal/casual) to guide correction style.
- Wrap this in a small Streamlit or web UI for non-technical users.

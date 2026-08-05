# Image Captioning Tool

Point it at an image file — your photo, an object, anything — and a
vision-enabled LLM generates a short, descriptive caption for it.

## Project structure

```
image_captioner/
├── cli.py                    Interactive command-line interface
├── captioner.py                Core captioning logic (reusable, testable)
├── config.py                  Loads settings from .env — no hardcoded secrets
├── tests/
│   └── test_captioner.py      Unit tests with a mocked LLM client
├── .env.example                Template for your local .env — fill this in
├── .gitignore                   Excludes .env, venv, caches, test images
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

> **Important:** this tool needs a *vision-capable* model, not a regular
> text chat model. Check `VISION_MODEL_NAME` in `.env.example` and
> confirm it's still a valid, currently-available model by checking
> https://console.groq.com/docs/models — provider vision-model names
> and availability change over time, so if you get a "model not found"
> error, this is the first thing to check.

## Run

```bash
python cli.py
```

Example session:

```
=======================================================
  Image Captioning Tool
=======================================================
Enter the path to an image file (jpg, png, webp, gif).
Type 'exit' to quit.

Image path: C:\Users\you\Pictures\my_dog.jpg

Caption: A golden retriever sitting on grass in bright afternoon sunlight.

Image path: exit
Goodbye!
```

Tip: you can drag-and-drop the image file into most terminals to
auto-fill its full path instead of typing it manually.

## Design notes

- **`validate_image_path()`** checks the file exists, is a supported
  type (jpg/jpeg/png/webp/gif), and isn't too large (20 MB default,
  matching Groq's documented per-image limit)
  *before* reading or encoding it — fails fast with a clear message
  rather than sending something the API will reject anyway.
- **Base64 data URL encoding** — images are sent as
  `data:image/jpeg;base64,...` inline in the request, which is the
  standard way OpenAI-compatible vision APIs accept image input (no
  separate file upload endpoint needed).
- **`temperature=0.4`** keeps captions fairly consistent and factual
  rather than overly creative or embellished.
- **One-sentence constraint** — the prompt explicitly asks for a single
  short sentence with no quotation marks, so output is clean and ready
  to use directly (e.g. as alt text or a filename suggestion).

## Testing

```bash
pytest
```

Tests use a mocked LLM client and temporary throwaway files (via
pytest's `tmp_path` fixture), so the suite runs instantly without a
real API key, network call, or actual photo. Covers:

- accepted vs. unsupported file extensions
- missing file handling
- oversized file rejection
- empty path validation
- successful caption parsing (stripped whitespace)
- empty-response handling
- API failure wrapping

## Switching to OpenAI instead of Groq

Edit `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-real-openai-key
VISION_MODEL_NAME=gpt-4o-mini
```

`gpt-4o-mini` and `gpt-4o` both support vision on OpenAI as of this
writing — double-check current availability at
https://platform.openai.com/docs/models.

## Troubleshooting

- **"GROQ_API_KEY is missing"** — `.env` wasn't created/filled in, or
  you're running from a different folder than the one containing it.
- **401 / authentication error** — key is wrong, expired, or revoked.
  Get a fresh one at https://console.groq.com/keys.
- **"model not found" / 404 on the vision model** — the vision model
  name in `.env` is outdated or retired; check the provider's current
  model list and update `VISION_MODEL_NAME`.
- **"Unsupported file type"** — only jpg/jpeg/png/webp/gif are accepted;
  convert other formats (e.g. HEIC from iPhones) to one of these first.
- **"Image is X MB, which exceeds the 20 MB limit"** — compress or
  resize the image, or lower/raise `MAX_IMAGE_SIZE_MB` in `captioner.py`
  (Groq itself rejects anything over 20MB regardless of this setting)

## Possible extensions

- Accept multiple images in one run and print a caption for each.
- Add a `--style` option (e.g. "alt text", "social media caption",
  "detailed description") to vary the prompt.
- Wrap this in a small Streamlit app with a drag-and-drop upload widget
  instead of typing a file path.

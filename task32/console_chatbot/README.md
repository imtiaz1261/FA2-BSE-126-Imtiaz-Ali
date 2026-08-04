# Console Chatbot (with conversation memory)

A basic console chatbot that runs in a continuous loop until you type
`exit`. Every message is sent to the LLM along with the full prior
conversation, so the model keeps context across turns.

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

> **Never commit your real `.env` file or paste your API key into chats,
> docs, or screenshots.** `.env` is already excluded via `.gitignore` —
> only `.env.example` (with blanks) should ever be shared.

## Run

```bash
python chatbot.py
```

Example session:

```
Chatbot ready — provider: groq, model: llama-3.1-8b-instant
Type your message and press Enter. Type 'exit' to quit.

You: My name is Ijaz.

Bot: Nice to meet you, Ijaz! How can I help you today?

You: What's my name?

Bot: Your name is Ijaz.

You: exit
Goodbye!
```

The second answer works because `chatbot.py` keeps a running list of every
message (`conversation`) and sends the whole thing with each API call —
not just the latest message.

## How the context/memory works

```python
conversation = [{"role": "system", "content": "You are a helpful assistant."}]

# each turn:
conversation.append({"role": "user", "content": user_input})
response = client.chat.completions.create(model=MODEL_NAME, messages=conversation)
conversation.append({"role": "assistant", "content": reply})
```

Sending the growing `conversation` list (instead of just the newest
message) is what gives the model memory of earlier turns.

## Switching to OpenAI instead of Groq

Edit `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-real-openai-key
MODEL_NAME=gpt-4o-mini
```

## Troubleshooting

- **"GROQ_API_KEY is missing"** — `.env` wasn't created/filled in, or
  you're running the script from a different folder than the one
  containing it.
- **401 / authentication error** — key is wrong, expired, or revoked.
  Get a fresh one at https://console.groq.com/keys.
- **Model not found** — check https://console.groq.com/docs/models and
  update `MODEL_NAME` in `.env`.

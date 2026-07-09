# Task 4 — LangChain & LCEL Intro

Converts a standard chat-model API call into a basic LCEL (LangChain
Expression Language) chain using the `prompt | model | output_parser`
pattern.

## What it demonstrates

- **Standard call**: build a model, call `.invoke()` directly, manually
  extract `.content` from the response.
- **LCEL chain**: the same task rebuilt as `prompt | model | output_parser`
  — a pipeline of "Runnables" that automatically pass data from one step
  to the next.
- **The Runnable interface**: every LCEL component (`ChatPromptTemplate`,
  the chat model, `StrOutputParser`) shares the same `.invoke()`,
  `.stream()`, and `.batch()` methods, which is what makes the `|` pipe
  syntax possible.
- **Streaming an LCEL chain** with `.stream()`.

## Files

| File               | Purpose                                         |
|--------------------|--------------------------------------------------|
| `lcel_intro.py`    | Main script — run this                          |
| `requirements.txt` | Python dependencies                             |
| `secret_key.py`    | Your API key (never commit this file)           |
| `.gitignore`       | Keeps `secret_key.py` out of version control     |

## Setup

1. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```
   (macOS/Linux: `source venv/bin/activate`)

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Add your API key**

   Get a free key at [console.groq.com/keys](https://console.groq.com/keys),
   then open `secret_key.py` and set:
   ```python
   GROQ_API_KEY = "gsk_your_real_key_here"
   ```

## Usage

```
python lcel_intro.py
```
<img width="569" height="357" alt="Screenshot 2026-07-08 171554" src="https://github.com/user-attachments/assets/b806ed18-f3f4-49f9-8ced-de2fecf243a1" />

## Expected output

```
=== Standard call ===
Recursion is when a function calls itself to solve smaller instances of
the same problem. It continues until it reaches a base case that stops
the recursive calls.

=== LCEL chain (prompt | model | output_parser) ===
Recursion is when a function calls itself to solve smaller instances of
the same problem. It continues until it reaches a base case that stops
the recursive calls.

=== LCEL chain, streamed ===
Closures are functions that "remember" variables from the scope in which
they were created, even after that scope has finished executing...
```

## Key takeaway

The standard call and the LCEL chain produce the same result — LCEL isn't
doing anything magical, it's just composing the same building blocks
(prompt formatting → model call → output parsing) into a single reusable
pipeline that also gets `.stream()` and `.batch()` for free.

## Switching to OpenAI instead of Groq

Swap `ChatGroq` for `ChatOpenAI` (see the commented-out block in
`lcel_intro.py`) — the rest of the chain (`prompt`, `output_parser`, and
the `|` pipe syntax) stays exactly the same, since both model classes
implement the same Runnable interface.

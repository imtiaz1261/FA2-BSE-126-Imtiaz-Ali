# Recipe Chain — Strict JSON with Pydantic

An LCEL chain (`prompt | model | parser`) that asks an LLM for a recipe and
returns a **validated** JSON object — not just raw text that looks like
JSON.

## What it demonstrates

- Defining a strict output schema with a `Pydantic` `BaseModel` (`Recipe`:
  `name`, `ingredients`, `steps`)
- `PydanticOutputParser`, which:
  1. Auto-generates formatting instructions injected into the prompt so
     the model knows the exact JSON shape to produce
  2. Parses and **validates** the model's text output back into a real
     `Recipe` Python object — raising an error if the JSON is malformed
     or missing required fields, instead of silently accepting bad data
- The same `prompt | model | parser` LCEL pattern from the earlier task,
  just with a structured parser as the final link instead of
  `StrOutputParser`

## Files

| File                 | Purpose                                       |
|-----------------------|------------------------------------------------|
| `recipe_chain.py`    | Main script — run this                        |
| `requirements.txt`   | Python dependencies                           |
| `secret_key.py`      | Your API key (never commit this file)         |
| `.gitignore`         | Keeps `secret_key.py` out of version control   |

## Setup

1. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Add your API key** in `secret_key.py` (get a free one at
   [console.groq.com/keys](https://console.groq.com/keys)).

## Usage

**Interactive:**
```
python recipe_chain.py
```

**Command-line:**
```
python recipe_chain.py --dish "chicken biryani"
```

## Example output

```
=== Parsed Pydantic object ===
name: Chicken Biryani
ingredients: ['2 cups basmati rice', '500g chicken, cut into pieces', ...]
steps: ['Marinate the chicken in yogurt and spices for 30 minutes', ...]

=== Strict JSON ===
{
  "name": "Chicken Biryani",
  "ingredients": [
    "2 cups basmati rice",
    "500g chicken, cut into pieces",
    ...
  ],
  "steps": [
    "Marinate the chicken in yogurt and spices for 30 minutes",
    ...
  ]
}
```

## Why Pydantic here matters

Without validation, an LLM might return JSON with a typo'd key, a missing
field, or a string where a list was expected — and your downstream code
would crash somewhere unrelated later. `PydanticOutputParser` catches that
mismatch immediately, at the point the data leaves the chain, with a clear
error instead of a confusing bug three steps later.

## Notes

- `temperature=0` is set on the model to keep output more consistent and
  reduce the chance of malformed JSON.
- If the model occasionally returns invalid JSON (small/free models do
  this more often than larger ones), you can catch the parser's exception
  and retry — LangChain also has `OutputFixingParser` for auto-retrying
  with a "fix this JSON" follow-up call, if you want to extend this later.
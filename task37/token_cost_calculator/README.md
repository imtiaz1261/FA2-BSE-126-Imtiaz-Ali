# Tiktoken Token Counter + Groq Cost Calculator

A small Python project that:

- Counts tokens in a supplied prompt using `tiktoken`.
- Sends the prompt to Groq using the configured model.
- Counts the returned response tokens.
- Calculates approximate input/output/total cost using configured per-1M-token pricing.
- Uses `.env` for the API key so the secret is not committed to Git.

## Important token-counting note

`tiktoken` does not necessarily use the exact tokenizer of every Groq-hosted model. For `llama-3.3-70b-versatile`, this project falls back to `cl100k_base` when there is no native `tiktoken` model mapping. Therefore, the token count is an **approximation**, not an exact provider-side billing count.

## Setup on Windows

Use Python 3.11:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and put your Groq key in `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Then run:

```powershell

```

Or:

```powershell
py -3.11 app.py
```

## Pricing

The project currently contains configurable example pricing for:

`llama-3.3-70b-versatile`

Input: `$0.59 / 1M tokens`  
Output: `$0.79 / 1M tokens`

Always verify current Groq pricing before relying on the calculated amount for billing.

## Formula

```text
input_cost  = input_tokens / 1,000,000 × input_price_per_1M
output_cost = output_tokens / 1,000,000 × output_price_per_1M
total_cost  = input_cost + output_cost
```

## Security

Do not commit your real `.env` file. It is already included in `.gitignore`.

If an API key has been exposed publicly, rotate/revoke it in the provider dashboard and replace it with a new secret.
python app.py
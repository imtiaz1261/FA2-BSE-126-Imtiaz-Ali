# Natural Language Unit Conversion Chatbot

A Streamlit chatbot that interprets English and simple Urdu/Hinglish conversion questions with Groq tool calling, then performs the arithmetic in a deterministic Python engine. The LLM never calculates conversion values.

## Features

- Length, weight, temperature, and volume conversions with common aliases.
- Groq structured tool calling when `GROQ_API_KEY` is configured.
- Local regex parser fallback for common prompts, useful for demos and development.
- Clear validation errors, chat history, examples, and automated tests.

## Setup and run

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and add GROQ_API_KEY (optional for the local fallback)
streamlit run app.py
```

Open the local URL Streamlit prints (normally `http://localhost:8501`). Example prompts: `5 km ko miles mein convert karo`, `Convert 10 kg to pounds`, and `25 Celsius to Fahrenheit`.

## Architecture

`Streamlit UI → Groq tool call/local parser → validated ConversionRequest → conversion.convert_unit → formatted response`.

`conversion/converter.py` normalizes aliases, validates matching categories, and owns all constants/formulas. To add units, add its canonical entry to `UNITS` plus aliases to `ALIASES`; compatible linear units use a factor relative to the category base. Add a special formula only for non-linear units such as temperature.

## Tests and troubleshooting

Run `pytest`. If Groq reports an API error, check `GROQ_API_KEY`, model access, and network; the local fallback works when no key is set. Incomplete prompts receive an example of the required value-and-two-unit format.

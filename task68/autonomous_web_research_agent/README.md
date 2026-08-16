# Autonomous Web Research Agent

Autonomous Python 3.11 + Playwright + Groq research agent.

Flow:
Topic -> Planner -> Search -> Playwright browser -> extract text -> running notes
-> stopping controller -> cited report.

Hard termination controls prevent infinite loops:
- MAX_PAGES (default 8)
- MAX_SEARCH_ROUNDS (default 4)
- MAX_SECONDS (default 180)

The browser does not bypass CAPTCHAs, paywalls, authentication, or access controls.

## Install

```cmd
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

Create `.env`:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
MAX_PAGES=8
MAX_SEARCH_ROUNDS=4
MAX_SECONDS=180
```

## Run

```cmdpython -m agent.main "latest trends in renewable energy"
python -m agent.main "latest trends in renewable energy"
```

Report is saved in `reports/`.

## Tests

```cmd
pytest -q
```

## Important
The report uses numbered citations [1], [2], etc. and preserves source URLs.
Verify important claims and sources before publishing.

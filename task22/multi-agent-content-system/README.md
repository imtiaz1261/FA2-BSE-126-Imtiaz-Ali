# Multi-Agent AI Content Generation System

> Placeholder README for Step 1. The complete README (usage, architecture
> diagram, agent descriptions, examples) will be written in a later step.

## Architecture (high level)

Three specialized agents collaborate through a LangGraph workflow:

```
Topic --> [Researcher Agent] --> research summary
       --> [Writer Agent]    --> first draft
       --> [Editor Agent]    --> polished final content
```

## Project structure

```
multi-agent-content-system/
├── agents/       # researcher.py, writer.py, editor.py (added later)
├── prompts/      # Prompt templates, kept separate from agent logic
├── graph/        # LangGraph StateGraph definition (added later)
├── tools/        # web_search.py, export.py (added later)
├── services/     # LLM client wrapper, logging setup
├── models/       # Pydantic State/schema models (added later)
├── utils/
│   └── check_environment.py   # Step 1 — verifies setup is ready
├── config/
│   └── settings.py             # Step 1 — centralized, validated config
├── api/          # FastAPI app (added later)
├── cli/          # Typer/Rich CLI (added later)
├── tests/        # Unit tests
├── docs/         # Documentation
├── requirements.txt
├── .env / .env.example
└── .gitignore
```

## Step 1 status: Environment & configuration

```
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python utils/check_environment.py
```

Expected output: every package shows `[  OK  ]`, and configuration shows
`OK — settings loaded and validated successfully`.

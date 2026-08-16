# Jarvis-Lite — LLM Function Calling Module

A production-style LLM function-calling system: the assistant
automatically decides whether a query needs live data (weather, stock
price), calls the right Python function with validated arguments, and
composes a natural-language answer from the result — or answers
directly when no tool is needed.

## Flow implemented

```
User Query
    v
LLM (Groq, OpenAI-compatible tools API)
    v
Determine Tool Required  (LLM decides: tool_calls present or not)
    v
Function Calling Schema  (explicit JSON schema per tool, validated with jsonschema)
    v
Execute Python Function   (tools/*.py, wrapped in error handling + logging)
    v
Tool Result                (structured dict, sent back as a "tool" message)
    v
LLM                        (composes the final answer from the tool result)
    v
Final Response
```

## Structure
```
jarvis-lite-function-calling/
├── engine.py              # the function-calling loop (the flow above)
├── main.py                 # CLI entry point
├── tools/
│   ├── __init__.py           # TOOL_SCHEMAS + TOOL_REGISTRY (the extension point)
│   ├── weather_tool.py        # get_weather(city) -- Open-Meteo, no API key
│   └── stock_tool.py          # get_stock_price(symbol) -- yfinance, no API key
├── errors.py                # ToolNotFoundError, InvalidArgumentsError, ToolExecutionError
├── config.py, utils.py
├── .env                     # your Groq key, already filled in
└── requirements.txt, .env.example, .gitignore
```

## Setup
```bash
pip install -r requirements.txt
```
`.env` already has a Groq key filled in.

## Run
```bash
python main.py
```
Try:
- `What's the weather in Islamabad?` -> calls `get_weather`
- `What is the stock price of AAPL?` -> calls `get_stock_price`
- `Who wrote Romeo and Juliet?` -> answered directly, no tool call

## How tool selection works
Every request sends `TOOL_SCHEMAS` to Groq's chat completions endpoint
with `tool_choice="auto"` — the model itself decides, from the schema
descriptions and the query's phrasing, whether a tool applies. If it
calls one (or more), `engine.py` executes the corresponding Python
function, sends the structured result back as a `role: "tool"` message,
and asks the LLM again for the final answer. If it doesn't call a tool,
its first response *is* the final answer — no unnecessary round-trip.

## Adding a new tool
1. Create `tools/my_new_tool.py` exporting:
   - `SCHEMA` — an OpenAI/Groq-format function schema dict
   - the executable Python function (raises `ToolExecutionError` on failure)
2. Import both in `tools/__init__.py` and add them to `TOOL_SCHEMAS` / `TOOL_REGISTRY`.

`engine.py` never needs to change — it's fully generic over whatever's registered.

## Error handling
- **Invalid arguments** — every tool call's arguments are validated
  against that tool's JSON schema (`jsonschema.validate`) before
  execution; a failure returns a structured error to the LLM instead
  of crashing or calling the function with bad input.
- **Unavailable tool** — if the LLM names a tool that isn't in
  `TOOL_REGISTRY` (shouldn't happen since only registered schemas are
  sent, but guarded anyway), `ToolNotFoundError` is raised and handled.
- **API failures** — network/geocoding/ticker-lookup failures in the
  tools themselves raise `ToolExecutionError` with a clear message.
- **Unexpected errors** — a catch-all in `engine._execute_tool` ensures
  no single tool failure ever crashes the whole conversation; it's
  logged and returned to the LLM as a structured error it can explain.
- **Malformed tool-call arguments from the LLM** (bad JSON) — caught
  and treated as empty arguments, which then fails schema validation
  cleanly rather than raising a raw `JSONDecodeError`.

## Logging
Every tool call logs: which tool was selected, the arguments passed,
execution status (success/validation failure/execution error), and the
result — to both console and `logs/jarvis.log`.

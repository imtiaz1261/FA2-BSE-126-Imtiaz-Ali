# Custom Tool + LangChain Agent: Unit Converter

A custom-built LangChain tool (`unit_converter`) registered into a
Groq-powered tool-calling agent, plus a test script that verifies the
agent calls the tool only when the situation actually calls for it.

## Structure
```
custom-tool-agent/
├── unit_converter_tool.py   # the custom tool (length/weight/temperature)
├── agent.py                  # registers the tool into a LangChain agent
├── test_agent.py               # runs 8 test queries, checks tool-call behavior
├── config.py
├── .env                       # your key, already filled in
└── requirements.txt, .env.example, .gitignore
```

## Setup
```bash
pip install -r requirements.txt
```
`.env` already has a Groq key filled in.

## The tool
`unit_converter(value, from_unit, to_unit)` -- pure Python, no external
API, so its output is deterministic and testable on its own:
- **Length**: km, m, cm, miles, feet, inches
- **Weight**: kg, g, lbs, oz
- **Temperature**: celsius, fahrenheit, kelvin (non-linear, handled separately)

## Run the test suite
```bash
python test_agent.py
```
This sends 8 queries to the agent -- 4 that clearly need the tool
("Convert 10 km to miles") and 4 that clearly don't ("What's the
capital of France?") -- and checks, via
`AgentExecutor(return_intermediate_steps=True)`, whether a tool call
actually happened for each one. Output is a pass/fail table.

## Try it interactively
```python
from agent import build_agent_executor

executor = build_agent_executor()
result = executor.invoke({"input": "Convert 5 kg to lbs"})
print(result["output"])
print(result["intermediate_steps"])   # shows the actual tool call made
```

## Error handling
- Missing/invalid units -> the tool returns a clear `Error: ...` string
  (not an exception) so the agent can relay it back to the user gracefully
- Mismatched categories (e.g. kg -> miles) -> explicitly rejected with a
  message listing supported categories
- Missing `GROQ_API_KEY` -> clear error before any request is attempted

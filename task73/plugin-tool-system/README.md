# Dynamic Plugin Tool System

A plugin architecture for LLM tools — add, enable, or disable tools
(like "currency converter" or "stock checker") **without changing any
core agent code**, similar to how ChatGPT Plugins / the GPT Store work.

## How it actually achieves "no redeploy"

1. **Standard interface** (`core/base_plugin.py`) — every plugin is a
   class with `name`, `description`, `input_schema`, and `execute()`.
   That's the entire contract.
2. **Dynamic discovery** (`core/registry.py`) — `discover_plugins()`
   scans the `plugins/` folder and re-imports every `*_plugin.py` file
   **from scratch** on every single call (via `importlib.util` with a
   fresh module name each time, bypassing Python's module cache). Drop
   a new file in, and it's available on the next agent query — no
   restart, because the process never needed to "know about it in
   advance."
3. **Enable/disable state** lives in `plugins_state.json`, not in code.
   Toggling a plugin in the Admin UI writes to that file immediately;
   the agent re-reads it on every query.
4. **The agent** (`core/agent.py`) never imports or references any
   specific plugin — it only ever asks the registry "what's enabled
   right now?" That's what makes the whole thing swappable.

I verified this directly: while the Python process was still running,
I wrote a brand-new plugin file to disk, called `discover_plugins()`
again with no restart, and it appeared and executed successfully.

## Structure
```
plugin-tool-system/
├── core/
│   ├── base_plugin.py      # the standard tool interface (the whole contract)
│   ├── registry.py           # discovery, enable/disable, schema generation, execution
│   └── agent.py                # Groq tool-calling agent, driven entirely by the registry
├── plugins/
│   ├── calculator_plugin.py
│   ├── weather_plugin.py            # Open-Meteo, no API key
│   ├── currency_converter_plugin.py  # Frankfurter API, no API key
│   └── unit_converter_plugin.py
├── app.py                    # Streamlit: Chat tab + Admin tab (enable/disable, rescan)
├── main.py                     # CLI alternative to app.py
├── plugins_state.json           # auto-created; enable/disable state
├── config.py, utils.py
├── .env                        # your Groq key, already filled in
└── requirements.txt, .env.example, .gitignore
```

## Setup
```bash
pip install -r requirements.txt
```
`.env` already has a Groq key filled in.

## Run
```bash
streamlit run app.py
```
- **Chat tab** — talk to the agent normally.
- **Admin tab** — see every discovered plugin, toggle enabled/disabled,
  and a "Rescan" button. The bottom of the tab shows exactly which tool
  names are currently exposed to the LLM's function-calling schema.

Or, for a quick terminal test without Streamlit:
```bash
python main.py
```

## Try the "add a plugin live" demo yourself
1. Run `streamlit run app.py`, open the **Admin** tab, note the 4 plugins listed.
2. While it's still running, create `plugins/joke_plugin.py`:
   ```python
   from core.base_plugin import BasePlugin

   class JokePlugin(BasePlugin):
       name = "joke"
       description = "Tells a short joke."
       input_schema = {"type": "object", "properties": {}, "required": []}

       def execute(self):
           return "Why did the developer go broke? Because they used up all their cache."
   ```
3. Go back to the Admin tab and click **Rescan** — `joke` appears in the list, enabled by default.
4. Go to the Chat tab and ask *"Tell me a joke"* — the agent calls your brand-new plugin. No restart happened.

## Adding a real new tool
Create `plugins/my_tool_plugin.py`, subclass `BasePlugin`, fill in
`name`, `description`, `input_schema`, and `execute()`. That's it —
`core/registry.py` and `core/agent.py` never need to change.

## Error handling
- **Plugin not found / disabled** — `PluginNotFoundError`, returned to
  the LLM as a structured error instead of crashing.
- **Invalid arguments** — every call is validated against the plugin's
  `input_schema` via `jsonschema` before execution.
- **Execution failures** (bad ticker, unreachable API, unsupported
  units) — plugins raise `PluginExecutionError`, caught and relayed cleanly.
- **Unexpected errors** — a catch-all in `core/agent.py` ensures one
  broken plugin never crashes the whole conversation.
- **Malformed plugin files** (import errors, missing `name`) — logged
  and skipped during discovery, rather than crashing the scan.

## Logging
Every plugin selection, its arguments, execution status, and result
are logged to `logs/plugin_system.log`, along with every enable/disable
toggle and discovery scan.

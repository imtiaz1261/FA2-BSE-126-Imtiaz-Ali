"""
core/registry.py
------------------
The plugin registry: discovers plugins from the plugins/ folder at
runtime, tracks which are enabled/disabled (persisted to a small JSON
state file so toggles survive restarts), and exposes them to the
agent as function-calling schemas.

How "no redeploy" actually works here:
  - discover_plugins() re-scans the plugins/ folder and re-imports
    every *_plugin.py file FROM SCRATCH each time it's called (via
    importlib.util with a fresh unique module name) -- so dropping a
    new file into plugins/ makes it available on the very next call,
    with no process restart required. Editing an existing plugin file
    is picked up the same way (true hot-reload, not just enable/disable).
  - Enable/disable state lives in plugins_state.json, not in code --
    toggling it in the admin UI takes effect on the agent's next query.
"""

import importlib.util
import inspect
import json
import uuid
from pathlib import Path
from typing import Dict, List

import jsonschema

from config import PLUGINS_DIR, PLUGIN_STATE_FILE
from core.base_plugin import BasePlugin, PluginExecutionError
from utils import get_logger

logger = get_logger(__name__)


class PluginNotFoundError(Exception):
    """Raised when a requested plugin name isn't registered."""


class InvalidPluginArgumentsError(Exception):
    """Raised when a plugin call's arguments fail schema validation."""


class PluginRegistry:
    def __init__(self, plugins_dir: Path = PLUGINS_DIR, state_file: Path = PLUGIN_STATE_FILE):
        self.plugins_dir = Path(plugins_dir)
        self.state_file = Path(state_file)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------
    # Discovery (hot: re-scans and re-imports every call)
    # ----------------------------------------------------------------
    def discover_plugins(self) -> Dict[str, BasePlugin]:
        """Scan plugins_dir for *_plugin.py files and instantiate every
        BasePlugin subclass found. Returns {plugin_name: instance}."""
        discovered: Dict[str, BasePlugin] = {}

        for file_path in sorted(self.plugins_dir.glob("*_plugin.py")):
            try:
                module = self._import_fresh(file_path)
            except Exception as exc:
                logger.error("Failed to import plugin file '%s': %s", file_path.name, exc)
                continue

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is BasePlugin or not issubclass(obj, BasePlugin):
                    continue
                if obj.__module__ != module.__name__:
                    continue  # skip re-exported/imported classes from elsewhere
                try:
                    instance = obj()
                except Exception as exc:
                    logger.error("Failed to instantiate plugin class '%s': %s", obj.__name__, exc)
                    continue

                if not instance.name:
                    logger.warning("Plugin in '%s' has no 'name' set; skipping.", file_path.name)
                    continue

                discovered[instance.name] = instance

        logger.info("Discovered %d plugin(s): %s", len(discovered), list(discovered.keys()))
        return discovered

    @staticmethod
    def _import_fresh(file_path: Path):
        """Import a .py file as a brand-new module object every time,
        bypassing sys.modules caching, so edits/new files are always
        picked up without restarting the process."""
        unique_name = f"plugin_{file_path.stem}_{uuid.uuid4().hex[:8]}"
        spec = importlib.util.spec_from_file_location(unique_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # ----------------------------------------------------------------
    # Enable / disable state (persisted to plugins_state.json)
    # ----------------------------------------------------------------
    def _load_state(self) -> Dict[str, bool]:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read plugin state file, treating as empty: %s", exc)
            return {}

    def _save_state(self, state: Dict[str, bool]) -> None:
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def set_enabled(self, plugin_name: str, enabled: bool) -> None:
        state = self._load_state()
        state[plugin_name] = enabled
        self._save_state(state)
        logger.info("Plugin '%s' set to %s", plugin_name, "ENABLED" if enabled else "DISABLED")

    def list_all_with_status(self) -> List[dict]:
        """List every discovered plugin with its enabled/disabled status
        (new plugins default to enabled) -- used by the admin UI."""
        plugins = self.discover_plugins()
        state = self._load_state()
        return [
            {
                "name": p.name,
                "description": p.description,
                "enabled": state.get(p.name, True),
            }
            for p in plugins.values()
        ]

    # ----------------------------------------------------------------
    # What the agent actually uses
    # ----------------------------------------------------------------
    def get_enabled_plugins(self) -> Dict[str, BasePlugin]:
        plugins = self.discover_plugins()
        state = self._load_state()
        return {name: p for name, p in plugins.items() if state.get(name, True)}

    def get_tool_schemas(self) -> List[dict]:
        """Convert every enabled plugin into an OpenAI/Groq function-calling schema."""
        schemas = []
        for plugin in self.get_enabled_plugins().values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": plugin.name,
                    "description": plugin.description,
                    "parameters": plugin.input_schema,
                },
            })
        return schemas

    def execute(self, plugin_name: str, arguments: dict) -> str:
        """Validate arguments against the plugin's schema, then execute it."""
        enabled_plugins = self.get_enabled_plugins()
        plugin = enabled_plugins.get(plugin_name)
        if plugin is None:
            raise PluginNotFoundError(
                f"Plugin '{plugin_name}' is not available (not found, or currently disabled)."
            )

        try:
            jsonschema.validate(instance=arguments, schema=plugin.input_schema)
        except jsonschema.ValidationError as exc:
            raise InvalidPluginArgumentsError(
                f"Invalid arguments for '{plugin_name}': {exc.message}"
            ) from exc

        return plugin.execute(**arguments)

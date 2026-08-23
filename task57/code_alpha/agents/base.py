from typing import Protocol
from ..core.models import Task


class Agent(Protocol):
    """Stateless: reads/writes only via the Task object it's given."""
    def run(self, task: Task) -> Task: ...


# --- Stub agents -------------------------------------------------------
# Replace `run()` bodies with real LLM calls (Anthropic API) + tool use.
# Kept as no-op stubs here so the orchestration skeleton is runnable
# and testable on its own.

class Planner:
    def run(self, task: Task) -> Task:
        task.plan = [f"step: implement '{task.request}'"]
        return task


class Coder:
    def run(self, task: Task) -> Task:
        task.generation_attempts += 1
        task.diff = f"--- diff for {task.id} (attempt {task.generation_attempts}) ---"
        return task


class Fixer:
    def run(self, task: Task, failure_log: str) -> Task:
        task.fix_attempts += 1
        task.diff = f"--- patched diff for {task.id} (fix {task.fix_attempts}) ---"
        return task

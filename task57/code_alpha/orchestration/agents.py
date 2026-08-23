from dataclasses import dataclass, field
from typing import Callable, Optional
from .agent_prompts import (
    PLANNER_PROMPT, CODER_PROMPT, TESTER_PROMPT, REVIEWER_PROMPT, FIXER_PROMPT,
)


@dataclass
class AgentContext:
    """Shared task-scoped context object handed off between agent nodes.
    Each agent reads what it needs and appends its own output — nothing is
    hidden between steps, so a human (or the Reviewer) can see the full trail."""
    task_id: str
    task_description: str
    design_md: str = ""
    requirements_md: str = ""
    plan: str = ""
    diff: str = ""
    test_result: Optional[dict] = None   # {"passed": bool, "output": str}
    review: str = ""
    log: list[str] = field(default_factory=list)


# Swap these for real Anthropic Messages API calls (system prompt = the
# corresponding *_PROMPT.format(...), tools = AGENT_TOOLS[<name>] from
# agent_prompts.py). Kept as plain functions so the orchestrator and retry
# policy are testable without a live model.
Completer = Callable[[str], str]


def _default_completer(prompt: str) -> str:
    return "(stub) " + prompt.splitlines()[0]


class Planner:
    name = "planner"

    def __init__(self, complete: Completer = _default_completer):
        self.complete = complete

    def run(self, ctx: AgentContext) -> AgentContext:
        prompt = PLANNER_PROMPT.format(
            task_description=ctx.task_description, design_md=ctx.design_md)
        ctx.plan = self.complete(prompt)
        ctx.log.append(f"[planner] {ctx.plan[:80]}")
        return ctx


class Coder:
    name = "coder"

    def __init__(self, complete: Completer = _default_completer):
        self.complete = complete

    def run(self, ctx: AgentContext) -> AgentContext:
        prompt = CODER_PROMPT.format(task_description=ctx.task_description, plan=ctx.plan)
        ctx.diff = self.complete(prompt) or f"diff for {ctx.task_id}"
        ctx.log.append(f"[coder] produced diff for {ctx.task_id}")
        return ctx


class Tester:
    name = "tester"

    def __init__(self, run_tests_fn: Callable[[AgentContext], dict]):
        # run_tests_fn is the real pass/fail source (wraps SandboxExecutor in
        # production; a controllable stub in tests/demos).
        self.run_tests_fn = run_tests_fn

    def run(self, ctx: AgentContext) -> AgentContext:
        ctx.test_result = self.run_tests_fn(ctx)
        ctx.log.append(f"[tester] passed={ctx.test_result['passed']}")
        return ctx


class Reviewer:
    name = "reviewer"

    def __init__(self, complete: Completer = _default_completer):
        self.complete = complete

    def run(self, ctx: AgentContext) -> AgentContext:
        prompt = REVIEWER_PROMPT.format(diff=ctx.diff, requirements_md=ctx.requirements_md)
        ctx.review = self.complete(prompt) or "APPROVE"
        ctx.log.append(f"[reviewer] {ctx.review[:80]}")
        return ctx


class Fixer:
    name = "fixer"

    def __init__(self, complete: Completer = _default_completer):
        self.complete = complete

    def run(self, ctx: AgentContext, attempt: int, max_attempts: int) -> AgentContext:
        failure_output = ctx.test_result["output"] if ctx.test_result else ""
        prompt = FIXER_PROMPT.format(
            task_description=ctx.task_description, diff=ctx.diff,
            failure_output=failure_output, attempt=attempt, max_attempts=max_attempts,
        )
        patched = self.complete(prompt)
        ctx.diff = patched or ctx.diff
        ctx.log.append(f"[fixer] attempt {attempt}/{max_attempts}")
        return ctx

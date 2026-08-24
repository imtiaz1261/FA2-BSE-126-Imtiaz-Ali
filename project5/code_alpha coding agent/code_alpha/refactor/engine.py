import json
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from code_alpha.testing.runner import run_test_suite

from .quality_analysis import run_quality_checks, CodeSmell
from .prompts import REFACTOR_PROMPT, CONSERVATIVE_RULES, THOROUGH_RULES
from .apply import safe_apply_refactor, RefactorOutcome

Completer = Callable[[str], str]


def _stub_completer(prompt: str) -> str:
    return "JUSTIFICATION: (stub)\nEDITS: []"


@dataclass
class RefactorLogEntry:
    smell: CodeSmell
    justification: str
    outcome: str    # "applied" | "skipped_reverted" | "skipped_conflict" | "pending_human_approval"
    detail: str


@dataclass
class RefactorRunResult:
    ran: bool
    blocked_reason: Optional[str]
    applied: list[RefactorLogEntry] = field(default_factory=list)
    skipped: list[RefactorLogEntry] = field(default_factory=list)
    pending_human_approval: list[RefactorLogEntry] = field(default_factory=list)


_RESPONSE_RE = re.compile(r"JUSTIFICATION:\s*(.+?)\s*EDITS:\s*(\[.*\])", re.DOTALL)


class RefactorEngine:
    """Runs only after a green test suite. Flags quality issues, proposes a
    discrete refactor per issue with a one-line justification, applies it,
    and re-verifies against the full suite — auto-reverting on any
    regression. Structural changes (Thorough mode) are never auto-applied;
    they're queued for explicit human approval regardless of confidence."""

    def __init__(
        self,
        sandbox_session,
        repo_path: str,
        mode: str = "conservative",   # "conservative" | "thorough"
        completer: Optional[Completer] = None,
    ):
        if mode not in ("conservative", "thorough"):
            raise ValueError("mode must be 'conservative' or 'thorough'")
        self.sandbox = sandbox_session
        self.repo_path = repo_path
        self.mode = mode
        self.complete = completer or _stub_completer

    def run(self, files: list[str]) -> RefactorRunResult:
        gate = run_test_suite(self.sandbox, self.repo_path)
        if not gate.passed:
            return RefactorRunResult(
                ran=False,
                blocked_reason="test suite is not green — refactor engine never runs against red tests",
            )

        smells = run_quality_checks(self.sandbox, files)
        result = RefactorRunResult(ran=True, blocked_reason=None)

        for smell in smells:
            # Structural smells always need Thorough mode + human approval,
            # regardless of what mode the engine is currently running in.
            if smell.severity == "structural":
                if self.mode != "thorough":
                    continue  # not even proposed in Conservative mode
                entry = self._propose(smell)
                entry.outcome = "pending_human_approval"
                result.pending_human_approval.append(entry)
                continue

            entry = self._propose(smell)
            if not entry.justification or entry.detail == "no edits proposed":
                continue

            outcome = self._apply_with_revert(entry)
            if outcome.applied:
                entry.outcome = "applied"
                result.applied.append(entry)
            elif outcome.reverted:
                entry.outcome = "skipped_reverted"
                entry.detail = outcome.reason
                result.skipped.append(entry)
            else:
                entry.outcome = "skipped_conflict"
                entry.detail = outcome.reason
                result.skipped.append(entry)

        return result

    # -- internals -----------------------------------------------------

    def _propose(self, smell: CodeSmell) -> RefactorLogEntry:
        code_context = self.sandbox.read_file(smell.file)
        prompt = REFACTOR_PROMPT.format(
            mode=self.mode,
            mode_rules=(THOROUGH_RULES if self.mode == "thorough" else CONSERVATIVE_RULES),
            smell_kind=smell.kind, file=smell.file, line=smell.line, symbol=smell.symbol,
            smell_detail=smell.detail, code_context=code_context,
        )
        raw = self.complete(prompt)
        match = _RESPONSE_RE.search(raw)
        if not match:
            return RefactorLogEntry(smell=smell, justification="", outcome="skipped", detail="unparseable response")
        justification, edits_json = match.group(1).strip(), match.group(2)
        return RefactorLogEntry(smell=smell, justification=justification, outcome="proposed", detail=edits_json)

    def _apply_with_revert(self, entry: RefactorLogEntry) -> RefactorOutcome:
        try:
            items = json.loads(entry.detail)
        except json.JSONDecodeError:
            entry.detail = "no edits proposed"
            return RefactorOutcome(applied=False, reverted=False, reason="invalid JSON")
        if not items:
            entry.detail = "no edits proposed"
            return RefactorOutcome(applied=False, reverted=False, reason="no edits")

        def _run_full():
            return run_test_suite(self.sandbox, self.repo_path)

        return safe_apply_refactor(self.sandbox, items, _run_full)

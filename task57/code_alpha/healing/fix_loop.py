import json
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from code_alpha.testing.runner import run_test_suite, TestRunResult
from code_alpha.testing.failure_parser import FailureReport

from .static_analysis import run_static_analysis, format_for_coder, StaticIssue
from .fixer_prompts import ROOT_CAUSE_PROMPT, PATCH_PROMPT, PRIOR_ATTEMPTS_TEMPLATE
from .log import FixLoopLog, FixAttempt

Completer = Callable[[str], str]


class EditConflict(Exception):
    """Same semantics as codegen/apply.py's EditConflict: the file changed
    since the edit was planned, so we refuse to guess."""


def _stub_completer(prompt: str) -> str:
    if "Output a JSON array of edits" in prompt:
        return "[]"
    return "(stub diagnosis) real deployment sends this prompt to the Messages API"


@dataclass
class FixLoopResult:
    passed: bool
    iterations_used: int
    needs_human: bool
    summary: str
    static_issues: list[StaticIssue] = field(default_factory=list)


class FixLoop:
    """The self-correction loop: static analysis gate -> iterative
    diagnose-then-patch-then-retest (affected scope only) -> full suite once
    green -> iteration cap with a clear human-facing summary on exhaustion."""

    def __init__(
        self,
        sandbox_session,
        repo_path: str,
        max_iterations: int = 5,
        completer: Optional[Completer] = None,
        log_dir: str = ".codealpha/fix-logs",
    ):
        self.sandbox = sandbox_session
        self.repo_path = repo_path
        self.max_iterations = max_iterations
        self.complete = completer or _stub_completer

    def run(
        self,
        task_id: str,
        task_description: str,
        touched_files: list[str],
        test_scope: str | None = None,
        source_context: str = "",
    ) -> FixLoopResult:
        log = FixLoopLog(".codealpha/fix-logs", task_id)

        # -- 1. static analysis gate, before tests even run -----------------
        static_issues = run_static_analysis(self.sandbox, touched_files)
        if static_issues:
            fix_prompt = (
                "Static analysis found issues in code you just wrote. Fix "
                "them before tests run:\n" + format_for_coder(static_issues)
            )
            patch_json = self.complete(fix_prompt)
            try:
                self._try_apply_patch(patch_json)  # best-effort; test loop below is still the safety net
            except EditConflict:
                pass

        # -- 2. run affected-scope tests -----------------------------------
        result = run_test_suite(self.sandbox, self.repo_path, scope=test_scope)

        iteration = 0
        while not result.passed and iteration < self.max_iterations:
            iteration += 1
            failure = result.failures[0] if result.failures else None

            diagnosis = self._diagnose(
                task_description, failure, iteration, source_context, log,
            )
            patch_json = self._propose_patch(diagnosis)
            try:
                applied, patch_summary = self._try_apply_patch(patch_json)
            except EditConflict as e:
                applied, patch_summary = False, f"conflict: {e}"

            # re-run only the affected scope for speed, per iteration
            result = run_test_suite(self.sandbox, self.repo_path, scope=test_scope)

            log.record(FixAttempt(
                iteration=iteration, timestamp=time.time(), diagnosis=diagnosis,
                patch_summary=patch_summary, tests_passed_after=result.passed,
                test_output=(result.stdout + result.stderr)[:500],
            ))

        if result.passed:
            # full suite once, now that the affected scope is green
            full_result = run_test_suite(self.sandbox, self.repo_path, scope=None)
            return FixLoopResult(
                passed=full_result.passed, iterations_used=iteration, needs_human=not full_result.passed,
                summary=(
                    f"Fixed after {iteration} iteration(s); full suite "
                    f"{'passed' if full_result.passed else 'still has unrelated failures'}."
                ),
                static_issues=static_issues,
            )

        # -- exhausted max_iterations: escalate with a clear summary --------
        summary = self._escalation_summary(task_description, log, result)
        return FixLoopResult(
            passed=False, iterations_used=iteration, needs_human=True,
            summary=summary, static_issues=static_issues,
        )

    # -- internals -----------------------------------------------------

    def _diagnose(self, task_description, failure: Optional[FailureReport], iteration, source_context, log) -> str:
        prior = log.summarize_prior()
        prior_note = PRIOR_ATTEMPTS_TEMPLATE.format(prior_summary=prior) if prior else ""
        prompt = ROOT_CAUSE_PROMPT.format(
            task_description=task_description, attempt=iteration, max_attempts=self.max_iterations,
            test_name=failure.test_name if failure else "unknown",
            file=failure.file if failure else "unknown",
            line=failure.line if failure else "unknown",
            stack_trace=failure.stack_trace if failure else "",
            expected=failure.expected if failure else "unknown",
            actual=failure.actual if failure else "unknown",
            source_context=source_context, prior_attempts_note=prior_note,
        )
        return self.complete(prompt)

    def _propose_patch(self, diagnosis: str) -> str:
        return self.complete(PATCH_PROMPT.format(diagnosis=diagnosis))

    def _try_apply_patch(self, patch_json: str) -> tuple[bool, str]:
        """Applies edits through the sandbox session (write_file/read_file),
        not the local filesystem — LocalSandboxBackend works on a *copy* of
        the repo, so a patch must land inside that copy to be visible to the
        next test run. (In production, DockerGvisorBackend bind-mounts the
        repo read-write, so a host-side apply_edits() would also be visible
        inside the container — this sandbox-routed version works either way,
        which is why the loop always goes through self.sandbox rather than
        codegen/apply.py directly.)
        """
        try:
            items = json.loads(patch_json)
        except json.JSONDecodeError:
            return False, "patch was not valid JSON — skipped"
        if not items:
            return False, "no edits proposed"

        applied_files = []
        for item in items:
            op, path = item["op"], item["file_path"]
            if op == "create":
                self.sandbox.write_file(path, item["new_content"])
                applied_files.append(path)
                continue

            current = self.sandbox.read_file(path)
            lines = current.splitlines(keepends=True)
            start, end = item.get("start_line"), item.get("end_line")
            expected = item.get("expected_old_content")

            if op == "replace":
                actual_range = "".join(lines[start - 1: end])
                if expected is not None and actual_range != expected:
                    raise EditConflict(
                        f"{path}:{start}-{end} changed since this edit was planned.\n"
                        f"expected: {expected!r}\nfound: {actual_range!r}"
                    )
                lines[start - 1: end] = item["new_content"].splitlines(keepends=True)
            elif op == "insert":
                anchor = lines[start - 1] if start - 1 < len(lines) else ""
                if expected is not None and anchor != expected:
                    raise EditConflict(
                        f"{path}:{start} changed since this edit was planned.\n"
                        f"expected: {expected!r}\nfound: {anchor!r}"
                    )
                lines[start - 1: start - 1] = item["new_content"].splitlines(keepends=True)

            self.sandbox.write_file(path, "".join(lines))
            applied_files.append(path)

        return bool(applied_files), f"{len(applied_files)} edit(s) applied to {sorted(set(applied_files))}"

    def _escalation_summary(self, task_description: str, log: FixLoopLog, last_result: TestRunResult) -> str:
        attempts = log.read_all()
        lines = [
            f"Task '{task_description}' still failing after {len(attempts)} fix attempt(s). "
            f"Needs human review.",
            "",
            "What was tried:",
        ]
        for a in attempts:
            lines.append(f"  [{a['iteration']}] diagnosis: {a['diagnosis'][:150]}")
            lines.append(f"       patch: {a['patch_summary']}")
            lines.append(f"       result: still failing")
        lines.append("")
        lines.append(f"Last test output (truncated):\n{(last_result.stdout + last_result.stderr)[:500]}")
        return "\n".join(lines)

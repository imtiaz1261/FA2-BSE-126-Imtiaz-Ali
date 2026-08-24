from typing import Callable, Optional
from .prompts import TEST_GENERATION_PROMPT
from .framework_detector import detect_framework, FrameworkInfo
from .runner import run_test_suite, TestRunResult
from .coverage import run_coverage, compute_delta, CoverageDelta

Completer = Callable[[str], str]


def _stub_completer(prompt: str) -> str:
    return "# (stub) real deployment sends this prompt to the Messages API"


class TestingModule:
    def __init__(self, completer: Optional[Completer] = None):
        self.complete = completer or _stub_completer

    def detect_framework(self, repo_path: str) -> FrameworkInfo:
        return detect_framework(repo_path)

    def generate_tests(
        self, task_description: str, acceptance_criteria: str, diff: str,
        framework: str, existing_test_example: str = "",
    ) -> str:
        prompt = TEST_GENERATION_PROMPT.format(
            task_description=task_description, acceptance_criteria=acceptance_criteria,
            diff=diff, framework=framework, existing_test_example=existing_test_example,
        )
        return self.complete(prompt)

    def run_tests(self, sandbox_session, repo_path: str, scope: str | None = None) -> TestRunResult:
        return run_test_suite(sandbox_session, repo_path, scope=scope)

    def coverage_delta(
        self, sandbox_session, before_report: dict | None, scope: str | None = None,
    ) -> list[CoverageDelta]:
        after_report = run_coverage(sandbox_session, scope=scope)
        return compute_delta(before_report, after_report)

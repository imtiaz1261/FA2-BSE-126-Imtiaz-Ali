import time
from dataclasses import dataclass


class SandboxTimeout(Exception):
    pass


@dataclass
class ExecResult:
    passed: bool
    log: str


class SandboxExecutor:
    """Ephemeral, isolated execution. Replace body with real container
    lifecycle (spin up, apply diff, run tests, tear down)."""

    def __init__(self, timeout_seconds: int = 300):
        self.timeout_seconds = timeout_seconds

    def run_tests(self, diff: str) -> ExecResult:
        start = time.monotonic()
        # --- simulated container + test run goes here ---
        elapsed = time.monotonic() - start
        if elapsed > self.timeout_seconds:
            raise SandboxTimeout(f"exceeded {self.timeout_seconds}s")
        passed = "patched" in diff or "attempt 3" in diff  # demo heuristic only
        return ExecResult(passed=passed, log=f"ran tests for: {diff}")

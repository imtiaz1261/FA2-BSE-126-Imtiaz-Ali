import json
import os
import time
from dataclasses import dataclass, asdict


@dataclass
class FixAttempt:
    iteration: int
    timestamp: float
    diagnosis: str
    patch_summary: str      # short description of what the patch changed
    tests_passed_after: bool
    test_output: str          # truncated — full output stays in the test runner's own log


class FixLoopLog:
    """Append-only JSONL, one entry per fix attempt — the record a human
    reviews when the loop escalates, and what feeds `prior_attempts_note`
    so the Fixer doesn't repeat itself across iterations."""

    def __init__(self, log_dir: str, task_id: str):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, f"{task_id}.fixloop.jsonl")

    def record(self, attempt: FixAttempt) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(attempt)) + "\n")

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(l) for l in f if l.strip()]

    def summarize_prior(self) -> str:
        attempts = self.read_all()
        if not attempts:
            return ""
        lines = [f"  attempt {a['iteration']}: {a['diagnosis'][:100]} -> still failing" for a in attempts]
        return "\n".join(lines)

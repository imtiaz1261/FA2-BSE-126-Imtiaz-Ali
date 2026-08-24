import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class AuditEntry:
    timestamp: float
    task_id: str
    action: str          # "run_command" | "read_file" | "write_file" | "list_files" | "destroy"
    detail: str            # command text, file path, etc. — never the full file content
    allowed: bool
    error: str | None = None
    duration_ms: float | None = None


class AuditLog:
    """Append-only JSONL log, one line per call. Every SandboxSession method
    writes here before returning — including rejected/denied calls, so a
    policy violation attempt is as visible as a successful one."""

    def __init__(self, log_dir: str, task_id: str):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, f"{task_id}.audit.jsonl")
        self.task_id = task_id

    def record(self, action: str, detail: str, allowed: bool,
               error: str | None = None, duration_ms: float | None = None) -> None:
        entry = AuditEntry(
            timestamp=time.time(), task_id=self.task_id, action=action,
            detail=detail, allowed=allowed, error=error, duration_ms=duration_ms,
        )
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

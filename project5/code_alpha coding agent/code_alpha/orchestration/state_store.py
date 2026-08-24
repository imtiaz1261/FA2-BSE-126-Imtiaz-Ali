import json
import os
from .task_graph import TaskGraph


class RunStateStore:
    """Persists orchestration state to disk so a run survives a crash/restart.
    Production note: swap the JSON file for Redis Streams / a durable queue
    (per the tech-stack spec) — the interface (save/load) stays identical,
    so the orchestrator doesn't need to change.
    """

    def __init__(self, repo_root: str, run_id: str):
        self.dir = os.path.join(repo_root, ".codealpha", "runs")
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, f"{run_id}.json")
        self.run_id = run_id

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def save(self, graph: TaskGraph, extra: dict | None = None) -> None:
        payload = {"run_id": self.run_id, "graph": graph.to_dict(), "extra": extra or {}}
        # Write-then-rename so a crash mid-write never corrupts the last good state.
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, self.path)

    def load(self) -> tuple[TaskGraph, dict]:
        with open(self.path) as f:
            payload = json.load(f)
        return TaskGraph.from_dict(payload["graph"]), payload.get("extra", {})

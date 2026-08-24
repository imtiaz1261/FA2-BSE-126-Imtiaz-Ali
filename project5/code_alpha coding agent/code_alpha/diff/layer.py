from dataclasses import dataclass
from ..core.models import Task


@dataclass
class PullRequest:
    task_id: str
    diff: str
    spec: str
    logs: list
    needs_human_debug: bool


def package(task: Task) -> PullRequest:
    return PullRequest(
        task_id=task.id,
        diff=task.diff or "",
        spec=task.spec or "",
        logs=task.logs,
        needs_human_debug=task.needs_human_debug,
    )


def auto_approve_eligible(pr: PullRequest, low_risk_paths=("docs/", "tests/")) -> bool:
    # Placeholder policy: only auto-approve when the diff is flagged low-risk
    # and doesn't need human debugging.
    return (not pr.needs_human_debug) and any(p in pr.diff for p in low_risk_paths)

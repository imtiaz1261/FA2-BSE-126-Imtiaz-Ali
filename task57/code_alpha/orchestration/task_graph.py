import re
from dataclasses import dataclass, field
from enum import Enum, auto


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    PASSED = auto()
    FAILED = auto()
    NEEDS_HUMAN = auto()


@dataclass
class TaskNode:
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    history: list[str] = field(default_factory=list)  # short log of what happened each attempt


class TaskGraph:
    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}

    def add(self, node: TaskNode) -> None:
        self.nodes[node.id] = node

    def ready_tasks(self) -> list[TaskNode]:
        """Tasks whose dependencies have all PASSED and are not yet started/done —
        these can run now, and any two returned together are parallelizable."""
        return [
            n for n in self.nodes.values()
            if n.status == TaskStatus.PENDING
            and all(self.nodes[d].status == TaskStatus.PASSED for d in n.depends_on)
        ]

    def is_complete(self) -> bool:
        return all(n.status == TaskStatus.PASSED for n in self.nodes.values())

    def is_stuck(self) -> bool:
        """True if nothing is runnable and the graph isn't complete —
        either everything's blocked on a NEEDS_HUMAN task, or genuinely done."""
        return not self.ready_tasks() and not self.is_complete()

    def to_dict(self) -> dict:
        return {
            nid: {
                "description": n.description, "depends_on": n.depends_on,
                "status": n.status.name, "attempts": n.attempts, "history": n.history,
            } for nid, n in self.nodes.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskGraph":
        g = cls()
        for nid, n in data.items():
            g.add(TaskNode(
                id=nid, description=n["description"], depends_on=n["depends_on"],
                status=TaskStatus[n["status"]], attempts=n["attempts"], history=n["history"],
            ))
        return g


# tasks.md line format, e.g.:
#   - [ ] Add rate_limit field to User model (design.md: Data model) (depends: T1)
#   - [ ] Write rate-limit unit tests (parallel)
_LINE_RE = re.compile(r"-\s*\[( |x)\]\s*(.+)")
_DEPENDS_RE = re.compile(r"\(depends:\s*([^)]+)\)")


def parse_tasks_md(text: str) -> TaskGraph:
    """Parses a tasks.md checklist into a TaskGraph. Explicit `(depends: T1, T2)`
    tags are honored; a task with no explicit deps and not the first task
    defaults to depending on the immediately preceding task (i.e. sequential
    unless the doc says otherwise) — matching how tasks.md is written today."""
    graph = TaskGraph()
    prev_id = None
    counter = 0

    for line in text.splitlines():
        m = _LINE_RE.match(line.strip())
        if not m:
            continue
        counter += 1
        task_id = f"T{counter}"
        raw_desc = m.group(2)

        dep_match = _DEPENDS_RE.search(raw_desc)
        if dep_match:
            deps = [d.strip() for d in dep_match.group(1).split(",")]
        elif "(parallel)" in raw_desc:
            deps = []
        elif prev_id:
            deps = [prev_id]
        else:
            deps = []

        description = _DEPENDS_RE.sub("", raw_desc).replace("(parallel)", "").strip()
        graph.add(TaskNode(id=task_id, description=description, depends_on=deps))
        prev_id = task_id

    return graph

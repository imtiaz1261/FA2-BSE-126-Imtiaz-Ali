from dataclasses import dataclass
from .task_graph import TaskGraph, TaskStatus, parse_tasks_md
from .agents import AgentContext, Planner, Coder, Tester, Reviewer, Fixer
from .state_store import RunStateStore


class PausedForHuman(Exception):
    """Raised when a task exhausts its retries — run state is already
    persisted by this point, so the human can inspect it and call resume()."""
    def __init__(self, task_id: str, log: list[str]):
        self.task_id, self.log = task_id, log
        super().__init__(f"task {task_id} needs human input after max retries: {log}")


@dataclass
class RunResult:
    completed: bool
    paused_task_id: str | None = None


class Orchestrator:
    """Custom finite-state orchestrator (LangGraph-compatible design: each
    agent is a node, AgentContext is the state passed edge-to-edge — swap in
    a StateGraph here without changing agents.py or task_graph.py)."""

    def __init__(
        self,
        repo_root: str,
        run_id: str,
        run_tests_fn,
        max_retries: int = 3,
        completer=None,
    ):
        self.store = RunStateStore(repo_root, run_id)
        self.max_retries = max_retries
        self.planner = Planner(completer) if completer else Planner()
        self.coder = Coder(completer) if completer else Coder()
        self.tester = Tester(run_tests_fn)
        self.reviewer = Reviewer(completer) if completer else Reviewer()
        self.fixer = Fixer(completer) if completer else Fixer()

    # -- entrypoints ---------------------------------------------------

    def start(self, tasks_md: str, design_md: str, requirements_md: str) -> RunResult:
        graph = parse_tasks_md(tasks_md)
        self.store.save(graph, extra={"design_md": design_md, "requirements_md": requirements_md})
        return self._execute(graph, design_md, requirements_md)

    def resume(self) -> RunResult:
        """Reload the last persisted state and continue — completed/failed
        tasks are skipped, only PENDING/interrupted work resumes."""
        if not self.store.exists():
            raise FileNotFoundError(f"no persisted run: {self.store.path}")
        graph, extra = self.store.load()
        return self._execute(graph, extra.get("design_md", ""), extra.get("requirements_md", ""))

    # -- core loop -----------------------------------------------------

    def _execute(self, graph: TaskGraph, design_md: str, requirements_md: str) -> RunResult:
        while not graph.is_complete():
            batch = graph.ready_tasks()
            if not batch:
                # Nothing runnable and not complete -> something upstream is
                # stuck on NEEDS_HUMAN; state is already persisted, so stop here.
                stuck = next(n for n in graph.nodes.values() if n.status == TaskStatus.NEEDS_HUMAN)
                return RunResult(completed=False, paused_task_id=stuck.id)

            # Everything in `batch` has its dependencies satisfied, so these
            # are the parallelizable tasks for this round (executed here in
            # sequence for determinism in the demo; a real deployment would
            # dispatch each to a worker via the task queue concurrently).
            for node in batch:
                node.status = TaskStatus.RUNNING
                self.store.save(graph, {"design_md": design_md, "requirements_md": requirements_md})

                ctx = AgentContext(
                    task_id=node.id, task_description=node.description,
                    design_md=design_md, requirements_md=requirements_md,
                )
                try:
                    self._run_task(ctx, node)
                    node.status = TaskStatus.PASSED
                    node.history.append("passed")
                except PausedForHuman:
                    node.status = TaskStatus.NEEDS_HUMAN
                    self.store.save(graph, {"design_md": design_md, "requirements_md": requirements_md})
                    return RunResult(completed=False, paused_task_id=node.id)

                self.store.save(graph, {"design_md": design_md, "requirements_md": requirements_md})

        return RunResult(completed=True)

    def _run_task(self, ctx: AgentContext, node) -> None:
        self.planner.run(ctx)
        self.coder.run(ctx)
        self.tester.run(ctx)

        attempt = 0
        while not ctx.test_result["passed"]:
            attempt += 1
            node.attempts = attempt
            node.history.append(f"failed attempt {attempt}: {ctx.test_result['output']}")
            if attempt >= self.max_retries:
                raise PausedForHuman(node.id, ctx.log)

            self.fixer.run(ctx, attempt=attempt, max_attempts=self.max_retries)
            self.tester.run(ctx)

        self.reviewer.run(ctx)
        node.history.append(f"review: {ctx.review[:60]}")

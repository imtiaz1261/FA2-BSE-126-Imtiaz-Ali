import shutil
from code_alpha.orchestration.orchestrator import Orchestrator
from code_alpha.orchestration.task_graph import parse_tasks_md

REPO_ROOT = "orch_demo_repo"
shutil.rmtree(REPO_ROOT, ignore_errors=True)

TASKS_MD = """
- [ ] Add rate_limit field to User model (design.md: Data model)
- [ ] Add rate-limit check middleware (depends: T1)
- [ ] Write rate-limit unit tests (parallel)
- [ ] Wire middleware into /signup route (depends: T2, T3)
"""

# Controls how many times each task's tests fail before passing, to prove
# both the "retry then succeed" and "exhaust retries then pause" paths.
FAIL_COUNTS = {"T1": 0, "T2": 1, "T3": 0, "T4": 5}  # T4 fails more than max_retries
_attempt_counter = {}


def scripted_run_tests(ctx) -> dict:
    n = _attempt_counter.get(ctx.task_id, 0)
    _attempt_counter[ctx.task_id] = n + 1
    if n < FAIL_COUNTS.get(ctx.task_id, 0):
        return {"passed": False, "output": f"AssertionError in {ctx.task_id} (attempt {n + 1})"}
    return {"passed": True, "output": "ok"}


if __name__ == "__main__":
    print("== parsed task graph ==")
    graph = parse_tasks_md(TASKS_MD)
    for node in graph.nodes.values():
        print(f"  {node.id}: {node.description!r} depends_on={node.depends_on}")

    orch = Orchestrator(REPO_ROOT, run_id="run-001", run_tests_fn=scripted_run_tests, max_retries=3)

    print("\n== start() ==")
    result = orch.start(TASKS_MD, design_md="(design doc)", requirements_md="(requirements doc)")
    print(f"  completed={result.completed} paused_task_id={result.paused_task_id}")

    print("\n== state after pause (loaded from disk) ==")
    persisted_graph, _ = orch.store.load()
    for node in persisted_graph.nodes.values():
        print(f"  {node.id}: status={node.status.name} attempts={node.attempts}")

    print("\n== human fixes T4 externally, then resume() ==")
    FAIL_COUNTS["T4"] = 0  # simulate the human's fix landing
    _attempt_counter["T4"] = 0
    # Reset T4 back to PENDING so resume() retries it (a real human-in-the-loop
    # UI would do this after reviewing node.history for T4).
    persisted_graph.nodes["T4"].status = persisted_graph.nodes["T4"].status.__class__.PENDING
    orch.store.save(persisted_graph, {"design_md": "(design doc)", "requirements_md": "(requirements doc)"})

    result2 = orch.resume()
    print(f"  completed={result2.completed} paused_task_id={result2.paused_task_id}")

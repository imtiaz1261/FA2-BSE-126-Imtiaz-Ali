from .models import Task, TaskState
from .state_machine import transition
from ..agents.base import Planner, Coder, Fixer
from ..sandbox.executor import SandboxExecutor, SandboxTimeout
from ..diff.layer import package


class Orchestrator:
    def __init__(
        self,
        generation_retry_limit: int = 3,
        max_fix_iterations: int = 5,
        sandbox_timeout: int = 300,
    ):
        self.generation_retry_limit = generation_retry_limit
        self.max_fix_iterations = max_fix_iterations
        self.planner = Planner()
        self.coder = Coder()
        self.fixer = Fixer()
        self.sandbox = SandboxExecutor(timeout_seconds=sandbox_timeout)

    def run(self, task: Task):
        transition(task, TaskState.PLANNING)
        self.planner.run(task)

        transition(task, TaskState.GENERATING)
        if not self._generate(task):
            return self._fail(task, "generation retries exhausted")

        transition(task, TaskState.TESTING)
        return self._verify_and_fix(task)

    # -- internal steps ---------------------------------------------------

    def _generate(self, task: Task) -> bool:
        while task.generation_attempts < self.generation_retry_limit:
            self.coder.run(task)
            if task.diff:
                return True
        return False

    def _verify_and_fix(self, task: Task):
        while True:
            try:
                result = self.sandbox.run_tests(task.diff)
            except SandboxTimeout as e:
                return self._fail(task, f"sandbox timeout: {e}")

            task.logs.append(result.log)

            if result.passed:
                transition(task, TaskState.AWAITING_REVIEW)
                return package(task)

            if task.fix_attempts >= self.max_fix_iterations:
                # Don't discard silently: route to review flagged for a human.
                task.needs_human_debug = True
                transition(task, TaskState.AWAITING_REVIEW)
                return package(task)

            transition(task, TaskState.FIXING)
            self.fixer.run(task, result.log)
            transition(task, TaskState.TESTING)

    def _fail(self, task: Task, reason: str):
        task.failure_reason = reason
        transition(task, TaskState.FAILED)
        return package(task)

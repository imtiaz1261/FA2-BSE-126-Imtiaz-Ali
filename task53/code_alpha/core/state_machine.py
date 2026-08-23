from .models import TaskState

# Only these transitions are legal. Enforced centrally so failure policy
# can never be bypassed by an agent mutating state directly.
TRANSITIONS = {
    TaskState.QUEUED: {TaskState.PLANNING},
    TaskState.PLANNING: {TaskState.GENERATING, TaskState.FAILED},
    TaskState.GENERATING: {TaskState.TESTING, TaskState.FAILED},
    TaskState.TESTING: {TaskState.FIXING, TaskState.AWAITING_REVIEW, TaskState.FAILED},
    TaskState.FIXING: {TaskState.TESTING, TaskState.FAILED},
    TaskState.AWAITING_REVIEW: {TaskState.APPROVED, TaskState.REJECTED},
    TaskState.REJECTED: {TaskState.PLANNING},
    TaskState.APPROVED: set(),
    TaskState.FAILED: set(),
}


class IllegalTransition(Exception):
    pass


def transition(task, new_state: TaskState):
    allowed = TRANSITIONS.get(task.state, set())
    if new_state not in allowed:
        raise IllegalTransition(f"{task.state.name} -> {new_state.name} not allowed")
    task.state = new_state
    return task

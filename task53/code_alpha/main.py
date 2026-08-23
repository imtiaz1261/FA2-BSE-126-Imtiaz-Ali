from code_alpha.core.models import Task
from code_alpha.core.orchestrator import Orchestrator

if __name__ == "__main__":
    task = Task(id="task-001", request="Add input validation to /signup endpoint")
    result = Orchestrator().run(task)
    print(f"state={task.state.name} needs_human_debug={result.needs_human_debug}")
    print(f"diff={result.diff}")
    print(f"logs={result.logs}")

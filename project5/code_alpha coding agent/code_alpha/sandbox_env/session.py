import time
import uuid
from .policy import SecurityPolicy, PolicyViolation, check_command
from .audit import AuditLog
from .backend import ContainerBackend, ExecResult, get_backend


class SandboxSession:
    """One ephemeral, isolated sandbox per task. Exposes exactly four
    operations to the agent — run_command, read_file, write_file, list_files
    — every one policy-checked and audit-logged before it touches the
    backend. Nothing else is reachable from agent code.
    """

    def __init__(
        self,
        repo_path: str,
        task_id: str | None = None,
        policy: SecurityPolicy | None = None,
        audit_log_dir: str = ".codealpha/audit",
        backend: ContainerBackend | None = None,
    ):
        self.task_id = task_id or f"task-{uuid.uuid4().hex[:8]}"
        self.policy = policy or SecurityPolicy()
        self.audit = AuditLog(audit_log_dir, self.task_id)
        self.backend = backend or get_backend()
        self._started = False
        self._repo_path = repo_path

    # -- lifecycle -----------------------------------------------------

    def __enter__(self) -> "SandboxSession":
        self.backend.start(self._repo_path, self.policy)
        self._started = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.destroy()

    def destroy(self) -> None:
        if self._started:
            self.backend.destroy()
            self._started = False
        self.audit.record("destroy", detail=self.task_id, allowed=True)

    # -- audited, policy-checked command interface ------------------------

    def run_command(self, command: str) -> ExecResult:
        start = time.monotonic()
        try:
            check_command(command, self.policy)
        except PolicyViolation as e:
            self.audit.record("run_command", detail=command, allowed=False, error=str(e))
            raise

        result = self.backend.exec(command)
        self.audit.record(
            "run_command", detail=command, allowed=True,
            error=(result.stderr[:200] if result.exit_code != 0 else None),
            duration_ms=(time.monotonic() - start) * 1000,
        )
        return result

    def read_file(self, path: str) -> str:
        try:
            content = self.backend.read_file(path)
        except Exception as e:
            self.audit.record("read_file", detail=path, allowed=False, error=str(e))
            raise
        self.audit.record("read_file", detail=path, allowed=True)
        return content

    def write_file(self, path: str, content: str) -> None:
        try:
            self.backend.write_file(path, content)
        except Exception as e:
            self.audit.record("write_file", detail=path, allowed=False, error=str(e))
            raise
        self.audit.record("write_file", detail=f"{path} ({len(content)} bytes)", allowed=True)

    def list_files(self, path: str = ".") -> list[str]:
        files = self.backend.list_files(path)
        self.audit.record("list_files", detail=path, allowed=True)
        return files

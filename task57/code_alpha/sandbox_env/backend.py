import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Protocol

from .policy import SecurityPolicy

try:
    import resource  # POSIX-only (Linux/macOS) — not available on Windows
    _HAS_RESOURCE = True
except ImportError:
    _HAS_RESOURCE = False


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class ContainerBackend(Protocol):
    def start(self, repo_path: str, policy: SecurityPolicy) -> None: ...
    def exec(self, command: str) -> ExecResult: ...
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str) -> None: ...
    def list_files(self, path: str = ".") -> list[str]: ...
    def destroy(self) -> None: ...


# --------------------------------------------------------------------------
# Real backend: Docker + gVisor/Firecracker. Requires `docker` package and a
# daemon with the `runsc` (gVisor) runtime registered — this is the actual
# production path; it cannot run inside this sandbox demo (no Docker daemon
# here), but the code is complete and standard docker-py usage.
# --------------------------------------------------------------------------
try:
    import docker
    _HAS_DOCKER = True
except ImportError:
    _HAS_DOCKER = False


class DockerGvisorBackend:
    """One ephemeral container per session. Repo is bind-mounted read-write.
    Network is `none` by default; when a registry is allow-listed, the
    container is instead attached to a restricted network whose egress
    proxy only permits that registry's hosts (proxy config out of scope
    here — enforced upstream of this class by infra, not by docker-py)."""

    IMAGE = "code-alpha/sandbox-runtime:latest"

    def __init__(self):
        if not _HAS_DOCKER:
            raise RuntimeError("docker package not installed — `pip install docker`")
        self._client = docker.from_env()
        self._container = None
        self._policy: SecurityPolicy | None = None

    def start(self, repo_path: str, policy: SecurityPolicy) -> None:
        self._policy = policy
        network_mode = "none" if policy.network_default_deny and not policy.allowed_registries else "sandbox-egress"
        self._container = self._client.containers.run(
            self.IMAGE,
            command="tail -f /dev/null",   # idle; exec() runs actual commands
            detach=True,
            runtime="runsc",                 # gVisor — strong syscall-level isolation
            volumes={os.path.abspath(repo_path): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            network_mode=network_mode,
            mem_limit=f"{policy.memory_mb}m",
            nano_cpus=int(1_000_000_000 * min(policy.cpu_seconds / policy.timeout_seconds, 2)),
            storage_opt={"size": f"{policy.disk_quota_mb}m"} if policy.disk_quota_mb else None,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            read_only=False,   # /workspace is rw; rest of the image fs stays read-only via image build
            auto_remove=False,  # we call destroy() explicitly so audit/log capture happens first
        )

    def exec(self, command: str) -> ExecResult:
        result = self._container.exec_run(
            ["sh", "-c", command], demux=True,
        )
        stdout, stderr = result.output
        return ExecResult(
            exit_code=result.exit_code,
            stdout=(stdout or b"").decode(errors="replace"),
            stderr=(stderr or b"").decode(errors="replace"),
        )

    def read_file(self, path: str) -> str:
        return self.exec(f"cat {path}").stdout

    def write_file(self, path: str, content: str) -> None:
        # write via a heredoc to avoid shell-quoting issues with content
        self.exec(f"mkdir -p $(dirname {path})")
        self._container.put_archive("/workspace", _tar_single_file(path, content))

    def list_files(self, path: str = ".") -> list[str]:
        out = self.exec(f"find {path} -type f").stdout
        return [l for l in out.splitlines() if l]

    def destroy(self) -> None:
        if self._container:
            self._container.remove(force=True)
            self._container = None


def _tar_single_file(path: str, content: str):
    import io
    import tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        data = content.encode()
        info = tarfile.TarInfo(name=path)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    return buf


# --------------------------------------------------------------------------
# Local fallback backend: no Docker daemon required. Used by the demo/tests
# here, and usable as a low-isolation dev mode. Ephemeral working directory
# (copy of the repo) + best-effort resource limits via `resource.setrlimit`
# on POSIX. NOTE: this does NOT provide real container/network isolation —
# that guarantee only exists with DockerGvisorBackend in production.
# --------------------------------------------------------------------------
class LocalSandboxBackend:
    def __init__(self):
        self._workdir: str | None = None
        self._policy: SecurityPolicy | None = None

    def start(self, repo_path: str, policy: SecurityPolicy) -> None:
        self._policy = policy
        self._workdir = tempfile.mkdtemp(prefix="codealpha_sandbox_")
        shutil.copytree(repo_path, self._workdir, dirs_exist_ok=True)

    def _limits_preexec(self):
        if not _HAS_RESOURCE:
            return None  # resource module unavailable (e.g. Windows) — caps become best-effort via timeout only
        policy = self._policy

        def _set():
            resource.setrlimit(resource.RLIMIT_CPU, (policy.cpu_seconds, policy.cpu_seconds))
            mem_bytes = policy.memory_mb * 1024 * 1024
            try:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            except (ValueError, OSError):
                pass  # some platforms (e.g. macOS) restrict RLIMIT_AS; degrade gracefully
        return _set

    def exec(self, command: str) -> ExecResult:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        # Disables .pyc caching: a session's working dir can see multiple
        # rapid edits (e.g. Fixer patches) within one wall-clock second,
        # which Python's mtime-based cache invalidation can't distinguish
        # from "unchanged" — this guarantees each run sees current source.
        try:
            proc = subprocess.run(
                command, shell=True, cwd=self._workdir, env=env,
                capture_output=True, text=True,
                timeout=self._policy.timeout_seconds,
                preexec_fn=self._limits_preexec(),
            )
            return ExecResult(proc.returncode, proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired as e:
            return ExecResult(-1, e.stdout or "", (e.stderr or "") + "\n[killed: timeout]", timed_out=True)

    def _resolve(self, path: str) -> str:
        full = os.path.abspath(os.path.join(self._workdir, path))
        if not full.startswith(os.path.abspath(self._workdir)):
            raise PermissionError(f"path escapes sandbox working dir: {path}")
        return full

    def read_file(self, path: str) -> str:
        with open(self._resolve(path), encoding="utf-8", errors="replace") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        full = self._resolve(path)
        os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

    def list_files(self, path: str = ".") -> list[str]:
        base = self._resolve(path)
        results = []
        for root, _, files in os.walk(base):
            for fname in files:
                results.append(os.path.relpath(os.path.join(root, fname), self._workdir))
        return sorted(results)

    def destroy(self) -> None:
        if self._workdir and os.path.exists(self._workdir):
            shutil.rmtree(self._workdir, ignore_errors=True)
        self._workdir = None


def get_backend() -> ContainerBackend:
    """Picks DockerGvisorBackend when a daemon is actually usable, else the
    local fallback — same interface either way, so callers never branch on it."""
    if _HAS_DOCKER:
        try:
            docker.from_env().ping()
            return DockerGvisorBackend()
        except Exception:
            pass
    return LocalSandboxBackend()

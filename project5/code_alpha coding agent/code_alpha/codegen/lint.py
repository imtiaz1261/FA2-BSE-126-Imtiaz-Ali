import shutil
import subprocess
from dataclasses import dataclass

# file extension -> (tool name, command template). First tool found on PATH wins.
_FORMATTERS = {
    ".py": [("black", ["black", "-q", "{file}"]), ("ruff", ["ruff", "format", "{file}"])],
    ".js": [("prettier", ["prettier", "--write", "{file}"])],
    ".ts": [("prettier", ["prettier", "--write", "{file}"])],
    ".jsx": [("prettier", ["prettier", "--write", "{file}"])],
    ".tsx": [("prettier", ["prettier", "--write", "{file}"])],
}


@dataclass
class LintResult:
    file_path: str
    tool: str | None
    ran: bool
    output: str = ""


def run_formatter(file_path: str, timeout: int = 30) -> LintResult:
    """Runs the first available formatter for this file's extension.
    Gracefully skips (ran=False) if nothing's installed, rather than
    failing the whole generation step — formatting is best-effort polish,
    not a correctness gate."""
    ext = "." + file_path.rsplit(".", 1)[-1] if "." in file_path else ""
    for tool_name, cmd_template in _FORMATTERS.get(ext, []):
        if shutil.which(tool_name) is None:
            continue
        cmd = [c.format(file=file_path) for c in cmd_template]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return LintResult(file_path, tool_name, True, proc.stdout + proc.stderr)
        except (subprocess.SubprocessError, OSError) as e:
            return LintResult(file_path, tool_name, False, str(e))
    return LintResult(file_path, None, False, "no formatter available for this file type")


def run_formatters(file_paths: list[str]) -> list[LintResult]:
    return [run_formatter(p) for p in file_paths]

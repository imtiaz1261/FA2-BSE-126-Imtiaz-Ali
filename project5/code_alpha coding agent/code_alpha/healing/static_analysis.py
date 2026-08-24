import json
import re
import shutil
from dataclasses import dataclass


@dataclass
class StaticIssue:
    tool: str          # "ruff" | "mypy"
    file: str
    line: int
    code: str            # e.g. "F821", "arg-type"
    message: str
    severity: str          # "error" | "warning"


def _run_ruff(sandbox_session, files: list[str]) -> list[StaticIssue]:
    target = " ".join(files) if files else "."
    result = sandbox_session.run_command(f"ruff check --output-format=json {target}")
    if not result.stdout.strip():
        return []
    try:
        items = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [
        StaticIssue(
            tool="ruff", file=item["filename"], line=item["location"]["row"],
            code=item["code"] or "", message=item["message"], severity="error",
        )
        for item in items
    ]


_MYPY_LINE_RE = re.compile(r"^(.+?):(\d+):(?:\d+:)?\s*(error|warning|note):\s*(.+?)(?:\s*\[(.+)\])?$")


def _run_mypy(sandbox_session, files: list[str]) -> list[StaticIssue]:
    target = " ".join(files) if files else "."
    result = sandbox_session.run_command(f"mypy --no-error-summary {target}")
    issues = []
    for line in (result.stdout + result.stderr).splitlines():
        m = _MYPY_LINE_RE.match(line.strip())
        if m and m.group(3) in ("error", "warning"):
            file, lineno, severity, message, code = m.groups()
            issues.append(StaticIssue(
                tool="mypy", file=file, line=int(lineno),
                code=code or "", message=message, severity=severity,
            ))
    return issues


def run_static_analysis(sandbox_session, files: list[str] | None = None) -> list[StaticIssue]:
    """Runs linter + type-checker inside the sandbox and returns combined,
    structured issues. Each tool is skipped (not failed) if not installed —
    static analysis is a quality gate, not a hard dependency of the loop."""
    files = files or []
    issues: list[StaticIssue] = []

    if shutil.which("ruff"):
        issues += _run_ruff(sandbox_session, files)
    if shutil.which("mypy"):
        issues += _run_mypy(sandbox_session, files)

    return issues


def format_for_coder(issues: list[StaticIssue]) -> str:
    """Renders issues as feedback text for the Coder agent (Module 4/5) to
    address before tests ever run."""
    if not issues:
        return "No static analysis issues."
    lines = [f"{i.tool} {i.severity} {i.file}:{i.line} [{i.code}] {i.message}" for i in issues]
    return "\n".join(lines)

import json
import os
from dataclasses import dataclass


@dataclass
class FrameworkInfo:
    name: str              # "pytest" | "jest" | "go_test" | "unknown"
    run_command: str        # command to run the full suite
    scoped_command: str      # "{run_command} {target}" template for running a subset


def detect_framework(repo_path: str) -> FrameworkInfo:
    """Looks at config files (not just file extensions) to identify the test
    framework, matching how a human would figure it out."""
    def exists(*parts) -> bool:
        return os.path.exists(os.path.join(repo_path, *parts))

    # Python: pytest
    if exists("pytest.ini") or exists("setup.cfg") or exists("pyproject.toml") or exists("conftest.py"):
        if exists("pyproject.toml"):
            with open(os.path.join(repo_path, "pyproject.toml")) as f:
                if "pytest" in f.read():
                    return FrameworkInfo("pytest", "pytest -q", "pytest -q {target}")
        if exists("pytest.ini") or exists("conftest.py"):
            return FrameworkInfo("pytest", "pytest -q", "pytest -q {target}")

    # Fallback: any test_*.py / *_test.py files anywhere -> assume pytest
    for root, _, files in os.walk(repo_path):
        if any(f.startswith("test_") or f.endswith("_test.py") for f in files):
            return FrameworkInfo("pytest", "pytest -q", "pytest -q {target}")

    # JavaScript/TypeScript: jest
    if exists("package.json"):
        with open(os.path.join(repo_path, "package.json")) as f:
            pkg = json.load(f)
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "jest" in deps:
            return FrameworkInfo("jest", "npx jest", "npx jest {target}")

    # Go
    if exists("go.mod"):
        return FrameworkInfo("go_test", "go test ./...", "go test {target}")

    return FrameworkInfo("unknown", "", "")

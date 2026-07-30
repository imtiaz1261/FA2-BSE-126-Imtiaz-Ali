"""utils/check_environment.py — Verifies the local environment is ready
before any agent work begins.

Run this after installing requirements.txt and setting up .env:

    python utils/check_environment.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

MIN_SUPPORTED_PYTHON = (3, 10)
MAX_RECOMMENDED_PYTHON = (3, 12)

REQUIRED_PACKAGES: tuple[str, ...] = (
    "langgraph",
    "langchain",
    "openai",
    "duckduckgo_search",
    "pydantic",
    "pydantic_settings",
    "typer",
    "rich",
    "docx",  # python-docx imports as "docx"
    "reportlab",
    "markdown",
    "fastapi",
)


@dataclass
class EnvironmentReport:
    python_version: str = ""
    python_supported: bool = False
    package_status: dict[str, str] = field(default_factory=dict)
    settings_valid: bool = False
    settings_error: str | None = None
    missing_packages: list[str] = field(default_factory=list)


def check_python_version() -> tuple[str, bool]:
    version_tuple = sys.version_info[:2]
    version_str = f"{version_tuple[0]}.{version_tuple[1]}"
    supported = MIN_SUPPORTED_PYTHON <= version_tuple <= MAX_RECOMMENDED_PYTHON
    return version_str, supported


def check_package(package_name: str) -> str:
    try:
        module = __import__(package_name)
        version = getattr(module, "__version__", None)
        if version is None:
            import importlib.metadata

            try:
                version = importlib.metadata.version(package_name.replace("_", "-"))
            except importlib.metadata.PackageNotFoundError:
                version = "installed (version unknown)"
        return str(version)
    except ImportError:
        return "NOT INSTALLED"


def check_settings() -> tuple[bool, str | None]:
    """Attempts to load config.settings.get_settings() — this is the
    real test of whether .env is correctly configured, not just whether
    packages are installed."""
    try:
        from config.settings import get_settings

        get_settings()
        return True, None
    except Exception as e:
        return False, str(e)


def build_report() -> EnvironmentReport:
    report = EnvironmentReport()
    report.python_version, report.python_supported = check_python_version()

    for package_name in REQUIRED_PACKAGES:
        status = check_package(package_name)
        report.package_status[package_name] = status
        if status == "NOT INSTALLED":
            report.missing_packages.append(package_name)

    if not report.missing_packages:
        report.settings_valid, report.settings_error = check_settings()

    return report


def print_report(report: EnvironmentReport) -> None:
    print("=" * 60)
    print("ENVIRONMENT CHECK")
    print("=" * 60)

    python_status = "OK" if report.python_supported else "WARNING"
    print(f"\nPython version: {report.python_version} [{python_status}]")
    if not report.python_supported:
        print("  Recommended range: Python 3.10-3.12.")

    print("\nRequired packages:")
    for package_name, status in report.package_status.items():
        marker = "OK" if status != "NOT INSTALLED" else "MISSING"
        print(f"  [{marker:^7}] {package_name:<20} {status}")

    print("\nConfiguration (.env):")
    if report.missing_packages:
        print("  Skipped (install missing packages first)")
    elif report.settings_valid:
        print("  OK — settings loaded and validated successfully")
    else:
        print(f"  FAILED: {report.settings_error}")

    print("\n" + "=" * 60)
    if report.missing_packages:
        print(f"RESULT: {len(report.missing_packages)} package(s) missing.")
        print("Run: pip install -r requirements.txt")
    elif not report.settings_valid:
        print("RESULT: Packages OK, but configuration is invalid. See error above.")
    else:
        print("RESULT: Environment is ready.")
    print("=" * 60)


def main() -> None:
    report = build_report()
    print_report(report)

    if report.missing_packages or not report.settings_valid:
        sys.exit(1)


if __name__ == "__main__":
    main()

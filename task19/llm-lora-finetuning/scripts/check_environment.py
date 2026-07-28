"""check_environment.py — Verifies the local environment is correctly set
up before any fine-tuning work begins.

Run this after installing requirements.txt and before touching any other
script in this project:

    python scripts/check_environment.py

Checks performed:
    1. Python version is in the supported range (3.10-3.12 recommended).
    2. Every required package is installed and importable.
    3. Whether a CUDA-capable GPU is available (fine-tuning works on CPU
       too, just much slower — this is informational, not a failure).

Exits with a non-zero status code if any required package is missing, so
this script can also be used in a CI pipeline or a pre-flight check.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

MIN_SUPPORTED_PYTHON = (3, 10)
MAX_RECOMMENDED_PYTHON = (3, 12)

REQUIRED_PACKAGES: tuple[str, ...] = (
    "torch",
    "transformers",
    "datasets",
    "accelerate",
    "peft",
    "evaluate",
)


@dataclass
class EnvironmentReport:
    """Collects the results of every check so they can be printed
    together as one readable summary at the end."""

    python_version: str = ""
    python_supported: bool = False
    package_status: dict[str, str] = field(default_factory=dict)
    gpu_available: bool = False
    gpu_name: str | None = None
    missing_packages: list[str] = field(default_factory=list)


def check_python_version() -> tuple[str, bool]:
    """Returns the running Python version as a string, and whether it
    falls within the supported range for this project."""
    version_tuple = sys.version_info[:2]
    version_str = f"{version_tuple[0]}.{version_tuple[1]}"
    supported = MIN_SUPPORTED_PYTHON <= version_tuple <= MAX_RECOMMENDED_PYTHON
    return version_str, supported


def check_package(package_name: str) -> str:
    """Attempts to import a package and returns its version string, or
    'NOT INSTALLED' if the import fails.

    Using importlib here (rather than a hardcoded if/elif per package)
    keeps this function generic — adding a new required package later
    only means adding its name to REQUIRED_PACKAGES, no new code.
    """
    try:
        module = __import__(package_name)
        version = getattr(module, "__version__", "unknown version")
        return str(version)
    except ImportError:
        return "NOT INSTALLED"


def check_gpu() -> tuple[bool, str | None]:
    """Checks whether PyTorch can see a CUDA-capable GPU.

    Returns (False, None) gracefully if torch itself isn't installed yet,
    rather than raising — this function is safe to call even mid-setup.
    """
    try:
        import torch

        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0)
        return False, None
    except ImportError:
        return False, None


def build_report() -> EnvironmentReport:
    """Runs every check and assembles the results into one report."""
    report = EnvironmentReport()

    report.python_version, report.python_supported = check_python_version()

    for package_name in REQUIRED_PACKAGES:
        status = check_package(package_name)
        report.package_status[package_name] = status
        if status == "NOT INSTALLED":
            report.missing_packages.append(package_name)

    report.gpu_available, report.gpu_name = check_gpu()

    return report


def print_report(report: EnvironmentReport) -> None:
    """Prints a human-readable summary of the environment check."""
    print("=" * 60)
    print("ENVIRONMENT CHECK")
    print("=" * 60)

    python_status = "OK" if report.python_supported else "WARNING"
    print(f"\nPython version: {report.python_version} [{python_status}]")
    if not report.python_supported:
        print(
            "  Recommended range: Python 3.10-3.12. "
            "Outside this range, some packages below may fail to install "
            "or may only offer CPU-only builds."
        )

    print("\nRequired packages:")
    for package_name, status in report.package_status.items():
        marker = "OK" if status != "NOT INSTALLED" else "MISSING"
        print(f"  [{marker:^7}] {package_name:<15} {status}")

    print("\nGPU:")
    if report.gpu_available:
        print(f"  CUDA GPU detected: {report.gpu_name}")
        print("  Training will use the GPU automatically.")
    else:
        print("  No CUDA GPU detected (or torch not installed yet).")
        print("  Training will run on CPU — slower, but functional for a")
        print("  small model with a small dataset, which is what this")
        print("  project uses.")

    print("\n" + "=" * 60)
    if report.missing_packages:
        print(f"RESULT: {len(report.missing_packages)} package(s) missing.")
        print(f"Run: pip install -r requirements.txt")
    else:
        print("RESULT: Environment is ready.")
    print("=" * 60)


def main() -> None:
    report = build_report()
    print_report(report)

    if report.missing_packages:
        sys.exit(1)  # non-zero exit — useful for scripting/CI, and makes
        # the failure state unambiguous rather than just printed text


if __name__ == "__main__":
    main()

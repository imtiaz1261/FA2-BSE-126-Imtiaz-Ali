import os
from dataclasses import dataclass
from .framework_detector import FrameworkInfo, detect_framework
from .failure_parser import FailureReport, parse_pytest_junit_xml, parse_pytest_text


@dataclass
class TestRunResult:
    passed: bool
    framework: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    failures: list[FailureReport]


_JUNIT_PATH = ".codealpha/test-report.xml"


def run_test_suite(sandbox_session, repo_path: str, scope: str | None = None) -> TestRunResult:
    """Detects the framework, runs it inside the given sandbox session
    (Module 6's SandboxSession — so this inherits its resource caps, network
    policy, and audit log for free), and returns structured results.

    `scope`, if given, is a file/dir/test-id to run instead of the full suite
    (affected-scope runs — faster feedback loop during the Fix loop).
    """
    framework = detect_framework(repo_path)
    if framework.name == "unknown":
        return TestRunResult(False, "unknown", "", -1, "", "no test framework detected", [])

    if framework.name == "pytest":
        command = f"pytest -q --junitxml={_JUNIT_PATH}"
        if scope:
            command += f" {scope}"
    else:
        command = framework.scoped_command.format(target=scope) if scope else framework.run_command

    result = sandbox_session.run_command(command)

    failures: list[FailureReport] = []
    if framework.name == "pytest":
        try:
            xml_text = sandbox_session.read_file(_JUNIT_PATH)
            failures = parse_pytest_junit_xml(xml_text)
        except Exception:
            failures = parse_pytest_text(result.stdout + result.stderr)

    return TestRunResult(
        passed=(result.exit_code == 0),
        framework=framework.name,
        command=command,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        failures=failures,
    )

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class FailureReport:
    """Output schema consumed by the Fixer agent (orchestration/agents.py
    Fixer.run reads test_result['output'] — this is the structured form
    that gets rendered into that text, one entry per failing test)."""
    test_name: str
    file: str
    line: Optional[int]
    expected: Optional[str]
    actual: Optional[str]
    stack_trace: str

    def to_dict(self) -> dict:
        return asdict(self)


_ASSERTION_MSG_RE = re.compile(r"E\s+assert\s+(.+)")
_EXPECTED_ACTUAL_RE = re.compile(r"E\s+.*[Ee]xpected[:\s]+(.+?)\s*(?:\n|$).*[Aa]ctual[:\s]+(.+)", re.DOTALL)


def _guess_expected_actual(stack_trace: str) -> tuple[Optional[str], Optional[str]]:
    """Best-effort extraction from common assertion styles. Real Fixer
    prompts get the full stack_trace regardless, so a miss here just means
    less pre-digested structure, not lost information."""
    m = _EXPECTED_ACTUAL_RE.search(stack_trace)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    m = _ASSERTION_MSG_RE.search(stack_trace)
    if m and "==" in m.group(1):
        lhs, rhs = m.group(1).split("==", 1)
        return rhs.strip(), lhs.strip()  # pytest prints "assert <actual> == <expected>"
    return None, None


def parse_pytest_junit_xml(xml_text: str) -> list[FailureReport]:
    """Parses `pytest --junitxml=<file>` output — the reliable, structured
    path (vs. scraping the human-readable console output)."""
    root = ET.fromstring(xml_text)
    reports = []

    for testcase in root.iter("testcase"):
        failure = testcase.find("failure")
        error = testcase.find("error")
        node = failure if failure is not None else error
        if node is None:
            continue

        classname = testcase.get("classname", "")
        name = testcase.get("name", "")
        file_attr = testcase.get("file") or classname.replace(".", "/") + ".py"
        stack_trace = node.text or node.get("message", "")

        line_match = re.search(rf"{re.escape(file_attr)}:(\d+)", stack_trace)
        if not line_match:
            line_match = re.search(r":(\d+):", stack_trace)
        line = int(line_match.group(1)) if line_match else None

        expected, actual = _guess_expected_actual(stack_trace)

        reports.append(FailureReport(
            test_name=f"{classname}::{name}" if classname else name,
            file=file_attr, line=line, expected=expected, actual=actual,
            stack_trace=stack_trace.strip(),
        ))
    return reports


_PYTEST_SUMMARY_RE = re.compile(r"FAILED (\S+)::(\S+)(?:\s*-\s*(.*))?")


def parse_pytest_text(output: str) -> list[FailureReport]:
    """Fallback for when junitxml wasn't captured (e.g. a crash before
    pytest could write it) — parses the `FAILED file::test - Error` summary
    lines pytest always prints, with a coarser stack_trace."""
    reports = []
    for match in _PYTEST_SUMMARY_RE.finditer(output):
        file_part, test_part, msg = match.group(1), match.group(2), match.group(3) or ""
        expected, actual = _guess_expected_actual(msg)
        reports.append(FailureReport(
            test_name=f"{file_part}::{test_part}", file=file_part, line=None,
            expected=expected, actual=actual, stack_trace=msg.strip(),
        ))
    return reports

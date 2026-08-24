import json
from dataclasses import dataclass


@dataclass
class FileCoverage:
    file: str
    percent_covered: float
    missing_lines: list[int]


@dataclass
class CoverageDelta:
    file: str
    before_percent: float | None   # None = file didn't exist before this change
    after_percent: float
    is_new_file: bool
    new_uncovered_lines: list[int]  # lines uncovered now that weren't uncovered before
    flagged_zero_coverage: bool      # True if any new code has 0% coverage — surfaced to Reviewer


def run_coverage(sandbox_session, scope: str | None = None) -> dict:
    """Runs `coverage run -m pytest` + `coverage json` inside the sandbox and
    returns the parsed coverage.py JSON report (per-file percent + missing
    lines) — the same report `compute_delta` diffs before vs. after."""
    target = f" {scope}" if scope else ""
    sandbox_session.run_command(f"coverage run -m pytest -q{target}")
    sandbox_session.run_command("coverage json -o .codealpha/coverage.json")
    raw = sandbox_session.read_file(".codealpha/coverage.json")
    return json.loads(raw)


def _file_percents(report: dict) -> dict[str, FileCoverage]:
    out = {}
    for file, data in report.get("files", {}).items():
        summary = data.get("summary", {})
        out[file] = FileCoverage(
            file=file,
            percent_covered=summary.get("percent_covered", 0.0),
            missing_lines=data.get("missing_lines", []),
        )
    return out


def compute_delta(before_report: dict | None, after_report: dict) -> list[CoverageDelta]:
    """Compares two coverage.py JSON reports and flags any *newly* uncovered
    line — i.e. a line missing coverage now that either didn't exist before
    or was covered before. This catches the common case precisely: a new
    function added inside an otherwise well-tested file, where the file's
    overall percentage barely moves but the new code itself has 0% coverage.
    `before_report=None` means this is the first run — every missing line
    in a file counts as newly uncovered.
    """
    before = _file_percents(before_report) if before_report else {}
    after = _file_percents(after_report)

    deltas = []
    for file, after_fc in after.items():
        before_fc = before.get(file)
        is_new = before_fc is None
        before_missing = set(before_fc.missing_lines) if before_fc else set()
        new_uncovered = sorted(set(after_fc.missing_lines) - before_missing)
        deltas.append(CoverageDelta(
            file=file,
            before_percent=(before_fc.percent_covered if before_fc else None),
            after_percent=after_fc.percent_covered,
            is_new_file=is_new,
            new_uncovered_lines=new_uncovered,
            flagged_zero_coverage=bool(new_uncovered),
        ))
    return deltas

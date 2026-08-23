from dataclasses import dataclass


class RefactorEditConflict(Exception):
    pass


def _apply_edits(sandbox_session, items: list[dict]) -> dict[str, str]:
    """Applies edits through the sandbox (write_file/read_file) — same
    sandbox-routed approach as Module 8's fix loop, and for the same reason:
    LocalSandboxBackend works on a copy, so edits must land inside it to be
    visible to the next test run. Returns {file_path: original_content}
    snapshots, taken *before* any write, so the caller can revert exactly.
    """
    snapshots: dict[str, str] = {}
    for item in items:
        path = item["file_path"]
        if path not in snapshots:
            snapshots[path] = sandbox_session.read_file(path)

        lines = sandbox_session.read_file(path).splitlines(keepends=True)
        start, end = item.get("start_line"), item.get("end_line")
        expected = item.get("expected_old_content")

        if item["op"] == "replace":
            actual_range = "".join(lines[start - 1: end])
            if expected is not None and actual_range != expected:
                raise RefactorEditConflict(
                    f"{path}:{start}-{end} changed since this refactor was planned"
                )
            lines[start - 1: end] = item["new_content"].splitlines(keepends=True)
        elif item["op"] == "insert":
            anchor = lines[start - 1] if start - 1 < len(lines) else ""
            if expected is not None and anchor != expected:
                raise RefactorEditConflict(f"{path}:{start} changed since this refactor was planned")
            lines[start - 1: start - 1] = item["new_content"].splitlines(keepends=True)

        sandbox_session.write_file(path, "".join(lines))
    return snapshots


def _revert(sandbox_session, snapshots: dict[str, str]) -> None:
    for path, original in snapshots.items():
        sandbox_session.write_file(path, original)


@dataclass
class RefactorOutcome:
    applied: bool
    reverted: bool
    reason: str


def safe_apply_refactor(sandbox_session, items: list[dict], run_full_tests) -> RefactorOutcome:
    """Applies one refactor's edits, re-runs the FULL test suite (not a
    scoped subset — a refactor can affect any caller), and auto-reverts
    if anything regresses. `run_full_tests` is a zero-arg callable returning
    a TestRunResult-like object with `.passed`.
    """
    try:
        snapshots = _apply_edits(sandbox_session, items)
    except RefactorEditConflict as e:
        return RefactorOutcome(applied=False, reverted=False, reason=str(e))

    result = run_full_tests()
    if result.passed:
        return RefactorOutcome(applied=True, reverted=False, reason="full suite green after refactor")

    _revert(sandbox_session, snapshots)
    return RefactorOutcome(
        applied=False, reverted=True,
        reason=f"reverted — full suite regressed after this refactor: exit_code={result.exit_code}",
    )

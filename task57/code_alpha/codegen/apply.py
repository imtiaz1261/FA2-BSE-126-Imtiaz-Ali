import os
from dataclasses import dataclass
from typing import Optional
from .schema import Edit, EditOp


class EditConflict(Exception):
    """Raised when an edit's expected_old_content doesn't match what's
    actually on disk — the file changed since the edit was planned. We
    refuse to guess; the caller must re-plan against current content."""


@dataclass
class ApplyResult:
    file_path: str
    op: EditOp
    applied: bool
    error: Optional[str] = None


def _atomic_write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)  # atomic on POSIX and Windows (same volume)


def _apply_one(edit: Edit) -> ApplyResult:
    if edit.op == EditOp.CREATE:
        if os.path.exists(edit.file_path):
            return ApplyResult(edit.file_path, edit.op, False,
                                error="file already exists — use replace/insert to modify it")
        _atomic_write(edit.file_path, edit.new_content)
        return ApplyResult(edit.file_path, edit.op, True)

    if not os.path.exists(edit.file_path):
        return ApplyResult(edit.file_path, edit.op, False,
                            error="file does not exist — use create first")

    with open(edit.file_path, encoding="utf-8") as f:
        lines = f.readlines()

    if edit.op == EditOp.REPLACE:
        current = "".join(lines[edit.start_line - 1: edit.end_line])
        if edit.expected_old_content is not None and current != edit.expected_old_content:
            raise EditConflict(
                f"{edit.file_path}:{edit.start_line}-{edit.end_line} changed since "
                f"this edit was planned.\nexpected:\n{edit.expected_old_content!r}\n"
                f"found:\n{current!r}"
            )
        new_lines = edit.new_content.splitlines(keepends=True)
        lines[edit.start_line - 1: edit.end_line] = new_lines

    elif edit.op == EditOp.INSERT:
        anchor = lines[edit.start_line - 1] if edit.start_line - 1 < len(lines) else ""
        if edit.expected_old_content is not None and anchor != edit.expected_old_content:
            raise EditConflict(
                f"{edit.file_path}:{edit.start_line} changed since this edit was planned.\n"
                f"expected line: {edit.expected_old_content!r}\nfound: {anchor!r}"
            )
        new_lines = edit.new_content.splitlines(keepends=True)
        lines[edit.start_line - 1: edit.start_line - 1] = new_lines

    _atomic_write(edit.file_path, "".join(lines))
    return ApplyResult(edit.file_path, edit.op, True)


def apply_edits(edits: list[Edit]) -> list[ApplyResult]:
    """Applies a batch of edits safely.

    - Groups by file, applies line-touching edits **highest line number
      first**, so earlier edits in the same file don't shift the line
      numbers a later edit expects.
    - CREATE edits run first (so a later edit in the same batch can target
      a file the batch itself just created).
    - Raises EditConflict immediately on a mismatch rather than partially
      applying a batch against stale content — the caller decides whether
      to re-plan or abort the whole task.
    """
    results: list[ApplyResult] = []

    creates = [e for e in edits if e.op == EditOp.CREATE]
    others = [e for e in edits if e.op != EditOp.CREATE]

    for edit in creates:
        results.append(_apply_one(edit))

    by_file: dict[str, list[Edit]] = {}
    for edit in others:
        by_file.setdefault(edit.file_path, []).append(edit)

    for file_edits in by_file.values():
        file_edits.sort(key=lambda e: e.start_line, reverse=True)
        for edit in file_edits:
            results.append(_apply_one(edit))

    return results

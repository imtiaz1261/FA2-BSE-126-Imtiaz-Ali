import ast
import difflib
import json
import shutil
from dataclasses import dataclass

COMPLEXITY_THRESHOLD = 8       # radon cyclomatic complexity above this is flagged
LONG_FUNCTION_LINES = 40         # functions longer than this are flagged
DUPLICATION_SIMILARITY = 0.9      # difflib ratio above this counts as duplicated
POOR_NAMES = {"tmp", "temp", "foo", "bar", "data", "val", "x1", "x2", "obj", "thing"}


@dataclass
class CodeSmell:
    kind: str          # "high_complexity" | "long_function" | "duplication" |
                        # "poor_naming" | "dead_code"
    file: str
    line: int
    symbol: str
    detail: str
    severity: str        # "conservative" — safe, local fix | "structural" — needs Thorough mode


def _run_radon_complexity(sandbox_session, files: list[str]) -> list[CodeSmell]:
    if not shutil.which("radon"):
        return []
    target = " ".join(files) if files else "."
    result = sandbox_session.run_command(f"radon cc --json {target}")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    smells = []
    for file, entries in report.items():
        for entry in entries:
            length = entry["endline"] - entry["lineno"]
            if entry["complexity"] > COMPLEXITY_THRESHOLD:
                smells.append(CodeSmell(
                    kind="high_complexity", file=file, line=entry["lineno"], symbol=entry["name"],
                    detail=f"cyclomatic complexity {entry['complexity']} (threshold {COMPLEXITY_THRESHOLD})",
                    severity="conservative" if entry["complexity"] <= COMPLEXITY_THRESHOLD * 2 else "structural",
                ))
            if length > LONG_FUNCTION_LINES:
                smells.append(CodeSmell(
                    kind="long_function", file=file, line=entry["lineno"], symbol=entry["name"],
                    detail=f"{length} lines (threshold {LONG_FUNCTION_LINES})",
                    severity="structural",  # splitting a function is a Thorough-mode change
                ))
    return smells


def _run_vulture_dead_code(sandbox_session, files: list[str]) -> list[CodeSmell]:
    if not shutil.which("vulture"):
        return []
    target = " ".join(files) if files else "."
    result = sandbox_session.run_command(f"vulture {target} --min-confidence 80")
    smells = []
    for line in result.stdout.splitlines():
        # vulture output: "file.py:12: unused function 'foo' (90% confidence)"
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        file, lineno = parts[0], parts[1]
        if not lineno.strip().isdigit():
            continue
        smells.append(CodeSmell(
            kind="dead_code", file=file, line=int(lineno), symbol="",
            detail=parts[2].strip(), severity="conservative",
        ))
    return smells


def _find_duplication(sandbox_session, files: list[str]) -> list[CodeSmell]:
    """Compares every function body in the given files pairwise; flags pairs
    above DUPLICATION_SIMILARITY as duplicated logic worth extracting."""
    functions = []  # (file, name, lineno, normalized_source)
    for file in files:
        if not file.endswith(".py"):
            continue
        try:
            source = sandbox_session.read_file(file)
            tree = ast.parse(source)
        except (SyntaxError, Exception):
            continue
        lines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno)
                body = "\n".join(lines[node.lineno:end])  # skip signature line, compare bodies
                if len(body.strip()) > 20:  # ignore trivial one-liners
                    functions.append((file, node.name, node.lineno, body))

    smells = []
    seen_pairs = set()
    for i, (f1, n1, l1, b1) in enumerate(functions):
        for f2, n2, l2, b2 in functions[i + 1:]:
            if (f1, n1) == (f2, n2):
                continue
            ratio = difflib.SequenceMatcher(None, b1, b2).ratio()
            if ratio >= DUPLICATION_SIMILARITY:
                pair_key = tuple(sorted([f"{f1}:{n1}", f"{f2}:{n2}"]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                smells.append(CodeSmell(
                    kind="duplication", file=f1, line=l1, symbol=n1,
                    detail=f"{ratio:.0%} similar to {n2} in {f2}:{l2} — candidate for extraction",
                    severity="conservative",
                ))
    return smells


def _find_poor_naming(sandbox_session, files: list[str]) -> list[CodeSmell]:
    smells = []
    for file in files:
        if not file.endswith(".py"):
            continue
        try:
            source = sandbox_session.read_file(file)
            tree = ast.parse(source)
        except (SyntaxError, Exception):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.lower() in POOR_NAMES:
                smells.append(CodeSmell(
                    kind="poor_naming", file=file, line=node.lineno, symbol=node.name,
                    detail=f"function name '{node.name}' doesn't describe what it does",
                    severity="conservative",
                ))
    return smells


def run_quality_checks(sandbox_session, files: list[str]) -> list[CodeSmell]:
    """Runs the full quality pass. Callers must only invoke this after the
    test suite is fully green — this module has no opinion on correctness,
    only on quality, and applying it against failing code conflates the two."""
    smells: list[CodeSmell] = []
    smells += _run_radon_complexity(sandbox_session, files)
    smells += _run_vulture_dead_code(sandbox_session, files)
    smells += _find_duplication(sandbox_session, files)
    smells += _find_poor_naming(sandbox_session, files)
    return smells

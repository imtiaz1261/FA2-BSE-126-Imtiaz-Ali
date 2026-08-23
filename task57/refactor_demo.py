import json
import os
import shutil
from code_alpha.sandbox_env.session import SandboxSession
from code_alpha.sandbox_env.policy import SecurityPolicy
from code_alpha.refactor.engine import RefactorEngine

REPO = "refactor_demo_repo"
shutil.rmtree(REPO, ignore_errors=True)
os.makedirs(REPO)

CALC = "calc.py"

_long_func_lines = ["def long_function(x):", "    total = 0"] + \
    [f"    total += {i}" for i in range(45)] + ["    return total"]

CALC_SOURCE = (
    "def _validate_numeric(a, b):\n"
    "    if not isinstance(a, (int, float)):\n"
    "        raise TypeError('a must be numeric')\n"
    "    if not isinstance(b, (int, float)):\n"
    "        raise TypeError('b must be numeric')\n"
    "\n"
    "def add(a, b):\n"
    "    _validate_numeric(a, b)\n"
    "    return a + b\n"
    "\n"
    "def subtract(a, b):\n"
    "    if not isinstance(a, (int, float)):\n"
    "        raise TypeError('a must be numeric')\n"
    "    if not isinstance(b, (int, float)):\n"
    "        raise TypeError('b must be numeric')\n"
    "    return a - b\n"
    "\n"
    "def tmp(x):\n"
    "    return x * 2\n"
    "\n"
    "def uses_tmp(x):\n"
    "    return tmp(x) + 1\n"
    "\n"
    + "\n".join(_long_func_lines) + "\n"
)

TEST_SOURCE = (
    "from calc import add, subtract, tmp, uses_tmp, long_function\n"
    "\n"
    "def test_add():\n"
    "    assert add(2, 3) == 5\n"
    "\n"
    "def test_subtract():\n"
    "    assert subtract(5, 2) == 3\n"
    "\n"
    "def test_uses_tmp():\n"
    "    assert uses_tmp(4) == 9\n"     # tmp(4)=8, +1 = 9 — breaks if tmp is renamed without updating this caller
    "\n"
    "def test_long_function():\n"
    "    assert long_function(0) == sum(range(45))\n"
)

with open(os.path.join(REPO, CALC), "w") as f:
    f.write(CALC_SOURCE)
with open(os.path.join(REPO, "test_calc.py"), "w") as f:
    f.write(TEST_SOURCE)


def _extract_code_context(prompt: str) -> str:
    return prompt.split("---\n", 1)[1].rsplit("\n---", 1)[0]


def scripted_completer(prompt: str) -> str:
    """Simulates proposals for each smell kind the analysis will find. Line
    numbers are computed from the prompt's *current* code_context (not
    hardcoded), so proposals stay valid even after an earlier refactor in
    the same run has shifted line numbers:
    - duplication (subtract vs _validate_numeric): a correct, safe extraction.
    - poor_naming ('tmp'): an INCOMPLETE rename — updates the definition but
      not uses_tmp()'s call site, which breaks test_uses_tmp and must
      trigger a genuine auto-revert (not a conflict) when the full suite
      re-runs and fails.
    - structural smells (long_function) never reach this function in
      Conservative mode; in Thorough mode the engine queues them for human
      approval without ever calling the completer to apply anything.
    """
    code = _extract_code_context(prompt)
    lines = code.splitlines()

    if "duplication" in prompt and "subtract" in prompt:
        start = next(i for i, l in enumerate(lines, 1) if "def subtract" in l) + 1
        block = lines[start - 1: start + 3]
        old_content = "".join(l + "\n" for l in block)
        edits = json.dumps([{
            "op": "replace", "file_path": "calc.py", "start_line": start, "end_line": start + 3,
            "new_content": "    _validate_numeric(a, b)\n", "expected_old_content": old_content,
        }])
        return f"JUSTIFICATION: extracted duplicated validation logic into shared _validate_numeric helper\nEDITS: {edits}"

    if "poor_naming" in prompt:
        lineno = next(i for i, l in enumerate(lines, 1) if l.strip() == "def tmp(x):")
        edits = json.dumps([{
            "op": "replace", "file_path": "calc.py", "start_line": lineno, "end_line": lineno,
            "new_content": "def double_value(x):\n", "expected_old_content": "def tmp(x):\n",
        }])
        return f"JUSTIFICATION: renamed tmp to double_value for clarity\nEDITS: {edits}"

    return "JUSTIFICATION: (no proposal)\nEDITS: []"


if __name__ == "__main__":
    policy = SecurityPolicy(timeout_seconds=30)

    print("== 1. gate: engine refuses to run against a red test suite ==")
    broken_repo = "refactor_demo_broken"
    shutil.rmtree(broken_repo, ignore_errors=True)
    os.makedirs(broken_repo)
    with open(os.path.join(broken_repo, "calc.py"), "w") as f:
        f.write("def add(a, b):\n    return a - b\n")
    with open(os.path.join(broken_repo, "test_calc.py"), "w") as f:
        f.write("from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n")
    with SandboxSession(broken_repo, task_id="refactor-gate-demo", policy=policy) as sess:
        engine = RefactorEngine(sess, broken_repo, mode="conservative")
        result = engine.run(files=["calc.py"])
        print(f"  ran={result.ran}  blocked_reason={result.blocked_reason!r}")

    print("\n== 2. Conservative mode against green tests ==")
    with SandboxSession(REPO, task_id="refactor-demo", policy=policy) as sess:
        engine = RefactorEngine(sess, REPO, mode="conservative", completer=scripted_completer)
        result = engine.run(files=[CALC])

        print(f"  ran={result.ran}")
        print(f"\n  applied ({len(result.applied)}):")
        for e in result.applied:
            print(f"    [{e.smell.kind}] {e.smell.symbol}: {e.justification}")
        print(f"\n  skipped/reverted ({len(result.skipped)}):")
        for e in result.skipped:
            print(f"    [{e.smell.kind}] {e.smell.symbol}: {e.detail}")
        print(f"\n  pending human approval in Conservative mode: {len(result.pending_human_approval)} (should be 0 — structural smells aren't even proposed here)")

        print("\n  == verifying: full suite still green after applied refactor, tmp() still works because it was reverted ==")
        from code_alpha.testing.runner import run_test_suite
        final = run_test_suite(sess, REPO)
        print(f"  final full-suite passed={final.passed}")

    print("\n== 3. Thorough mode — structural smells now surface, but only as pending approval ==")
    with SandboxSession(REPO, task_id="refactor-demo-thorough", policy=policy) as sess:
        engine = RefactorEngine(sess, REPO, mode="thorough", completer=scripted_completer)
        result = engine.run(files=[CALC])
        print(f"  pending_human_approval ({len(result.pending_human_approval)}):")
        for e in result.pending_human_approval:
            print(f"    [{e.smell.kind}] {e.smell.symbol}: {e.smell.detail}")
        print("  (none of these were written to disk — apply requires explicit human approval)")

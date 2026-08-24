import json
import os
import shutil
from code_alpha.sandbox_env.session import SandboxSession
from code_alpha.sandbox_env.policy import SecurityPolicy
from code_alpha.healing.fix_loop import FixLoop

REPO = "healing_demo_repo"
shutil.rmtree(REPO, ignore_errors=True)
os.makedirs(REPO)

CALC = "calc.py"  # sandbox-relative — the sandbox's working copy root, not the host REPO/ prefix
with open(os.path.join(REPO, CALC), "w") as f:
    f.write(
        "import os\n"                     # unused import — a real static-analysis hit
        "def add(a, b):\n"
        "    return a - b  # bug\n"
        "\n"
        "def divide(a, b):\n"
        "    return a / b\n"
    )
with open(os.path.join(REPO, "test_calc.py"), "w") as f:
    f.write(
        "from calc import add, divide\n"
        "\n"
        "def test_add():\n"
        "    assert add(2, 3) == 5\n"
        "\n"
        "def test_divide():\n"
        "    assert divide(10, 2) == 5\n"
    )


def scripted_completer(prompt: str) -> str:
    """Simulates a real model across the loop's steps:
    - Fixes the static-analysis issue (removes the unused import).
    - On the FIRST fix attempt, proposes no edit at all (a "couldn't find
      the cause" response) — proving the loop correctly treats that as a
      failed attempt and keeps going, not a false success.
    - On the SECOND fix attempt, proposes the correct patch.
    """
    if "Static analysis found issues" in prompt:
        return json.dumps([{
            "op": "replace", "file_path": CALC, "start_line": 1, "end_line": 1,
            "new_content": "", "expected_old_content": "import os\n",
        }])
    if "diagnosing a test failure" in prompt:
        n = scripted_completer.iteration = getattr(scripted_completer, "iteration", 0) + 1
        return (f"attempt {n}: test_add expects 5 for add(2, 3) but got -1; "
                f"add() at calc.py is subtracting instead of adding its two arguments.")
    if "Output a JSON array of edits" in prompt:
        if getattr(scripted_completer, "iteration", 0) < 2:
            return "[]"  # first attempt: no confident fix proposed
        return json.dumps([{
            "op": "replace", "file_path": CALC, "start_line": 2, "end_line": 2,
            "new_content": "    return a + b\n", "expected_old_content": "    return a - b  # bug\n",
        }])
    return ""


if __name__ == "__main__":
    policy = SecurityPolicy(timeout_seconds=30)
    with SandboxSession(REPO, task_id="healing-demo", policy=policy) as sess:
        loop = FixLoop(sess, REPO, max_iterations=5, completer=scripted_completer)

        print("== running the self-healing loop ==")
        result = loop.run(
            task_id="healing-demo",
            task_description="Fix add() to correctly sum its arguments",
            touched_files=[CALC],
            source_context="def add(a, b):\n    return a - b  # bug",
        )
        print(f"\npassed={result.passed} iterations_used={result.iterations_used} needs_human={result.needs_human}")
        print(f"static_issues_found={len(result.static_issues)}: {[i.code for i in result.static_issues]}")
        print(f"summary: {result.summary}")

        print("\n== fix-loop log (every attempt, for auditability) ==")
        from code_alpha.healing.log import FixLoopLog
        log = FixLoopLog(".codealpha/fix-logs", "healing-demo")
        for a in log.read_all():
            print(f"  [{a['iteration']}] passed_after={a['tests_passed_after']}  {a['diagnosis'][:70]}")

        print("\n== fixed content, read from inside the sandbox (not yet merged to the real repo — ")
        print("   per Module 6's design, that only happens after human approval) ==")
        print(sess.read_file(CALC))

    # -- unfixable case: proves the cap + escalation path -------------------
    print("\n\n== second run: a failure the scripted model can never fix (exhausts the cap) ==")
    shutil.rmtree(REPO, ignore_errors=True)
    os.makedirs(REPO)
    with open(os.path.join(REPO, CALC), "w") as f:
        f.write("def add(a, b):\n    return a - b  # never gets fixed by this stub\n")
    with open(os.path.join(REPO, "test_calc.py"), "w") as f:
        f.write("from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n")

    def never_fixes(prompt: str) -> str:
        if "diagnosing" in prompt:
            return "root cause not found from available evidence"
        if "Output a JSON array of edits" in prompt:
            return "[]"
        return ""

    with SandboxSession(REPO, task_id="healing-demo-2", policy=policy) as sess:
        loop2 = FixLoop(sess, REPO, max_iterations=3, completer=never_fixes)
        result2 = loop2.run(
            task_id="healing-demo-2", task_description="Fix add()",
            touched_files=[CALC], source_context="",
        )
        print(f"passed={result2.passed} iterations_used={result2.iterations_used} needs_human={result2.needs_human}")
        print(f"\nescalation summary shown to the human:\n{result2.summary}")

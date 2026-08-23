import os
import shutil
from code_alpha.sandbox_env.session import SandboxSession
from code_alpha.sandbox_env.policy import SecurityPolicy
from code_alpha.testing.engine import TestingModule

REPO = "testing_demo_repo"
shutil.rmtree(REPO, ignore_errors=True)
os.makedirs(REPO)

with open(os.path.join(REPO, "calc.py"), "w") as f:
    f.write(
        "def add(a, b):\n"
        "    return a - b  # bug: should be a + b\n"
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

if __name__ == "__main__":
    module = TestingModule()

    print("== 1. detect_framework() ==")
    framework = module.detect_framework(REPO)
    print(f"  {framework}")

    print("\n== 2. run_tests() inside the sandbox — one test fails (real bug) ==")
    policy = SecurityPolicy(timeout_seconds=30)
    with SandboxSession(REPO, task_id="testing-demo", policy=policy) as sess:
        result = module.run_tests(sess, REPO)
        print(f"  passed={result.passed} exit_code={result.exit_code}")

        print("\n== 3. structured failure report (what the Fixer agent receives) ==")
        for fr in result.failures:
            print(f"  test_name: {fr.test_name}")
            print(f"  file: {fr.file}  line: {fr.line}")
            print(f"  expected: {fr.expected!r}  actual: {fr.actual!r}")
            print(f"  stack_trace (first line): {fr.stack_trace.splitlines()[0] if fr.stack_trace else ''}")

        print("\n== 4. Fixer applies the fix, tests re-run ==")
        fixed = sess.read_file("calc.py").replace("a - b", "a + b")
        sess.write_file("calc.py", fixed)
        result2 = module.run_tests(sess, REPO)
        print(f"  passed={result2.passed} exit_code={result2.exit_code} failures={len(result2.failures)}")

        print("\n== 5. coverage delta — add an untested function, expect it flagged at 0% ==")
        before = None
        try:
            import json
            sess.run_command("coverage run -m pytest -q")
            sess.run_command("coverage json -o .codealpha/coverage.json")
            before = json.loads(sess.read_file(".codealpha/coverage.json"))
        except Exception as e:
            print(f"  (baseline coverage run skipped: {e})")

        untested = sess.read_file("calc.py") + "\ndef multiply(a, b):\n    return a * b\n"
        sess.write_file("calc.py", untested)

        deltas = module.coverage_delta(sess, before_report=before)
        for d in deltas:
            flag = f" <-- FLAGGED: new uncovered lines {d.new_uncovered_lines}" if d.flagged_zero_coverage else ""
            print(f"  {d.file}: before={d.before_percent} after={d.after_percent:.1f}%{flag}")

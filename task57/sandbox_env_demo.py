import os
import shutil
from code_alpha.sandbox_env.session import SandboxSession
from code_alpha.sandbox_env.policy import SecurityPolicy, PolicyViolation

SOURCE_REPO = "sandbox_demo_source_repo"
shutil.rmtree(SOURCE_REPO, ignore_errors=True)
os.makedirs(SOURCE_REPO)
with open(os.path.join(SOURCE_REPO, "app.py"), "w") as f:
    f.write("print('hello from the repo')\n")

if __name__ == "__main__":
    policy = SecurityPolicy(cpu_seconds=5, memory_mb=256, timeout_seconds=5)

    print("== 1. start an ephemeral session (repo mounted read-write) ==")
    with SandboxSession(SOURCE_REPO, task_id="demo-task-1", policy=policy) as sess:
        print(f"  backend: {type(sess.backend).__name__}")

        print("\n== 2. run_command — allowed command ==")
        result = sess.run_command("python3 app.py")
        print(f"  exit={result.exit_code} stdout={result.stdout.strip()!r}")

        print("\n== 3. write_file / read_file / list_files ==")
        sess.write_file("new_module.py", "def add(a, b):\n    return a + b\n")
        print(f"  read back: {sess.read_file('new_module.py')!r}")
        print(f"  files: {sess.list_files()}")

        print("\n== 4. denylisted command is rejected (never reaches the backend) ==")
        try:
            sess.run_command("sudo rm -rf /")
        except PolicyViolation as e:
            print(f"  correctly rejected: {e}")

        print("\n== 5. network default-deny: pip install rejected without allow-list ==")
        try:
            sess.run_command("pip install requests")
        except PolicyViolation as e:
            print(f"  correctly rejected: {e}")

        print("\n== 6. allow-list pypi, then the same command passes the policy check ==")
        policy.allow_registry("pypi")
        try:
            check_result = sess.run_command("pip install --dry-run requests")
            print(f"  policy check passed, command executed (exit={check_result.exit_code})")
        except PolicyViolation as e:
            print(f"  unexpectedly rejected: {e}")

        print("\n== 7. resource timeout is enforced ==")
        slow_result = sess.run_command("python3 -c \"import time; time.sleep(10)\"")
        print(f"  timed_out={slow_result.timed_out}")

    print("\n== 8. session destroyed — working dir is gone ==")
    # sess.backend._workdir was removed by __exit__; nothing left on disk for this task

    print("\n== 9. audit log — every call above, including rejected ones ==")
    for entry in sess.audit.read_all():
        status = "OK" if entry["allowed"] else "DENIED"
        print(f"  [{status:6s}] {entry['action']:12s} {entry['detail'][:50]}")

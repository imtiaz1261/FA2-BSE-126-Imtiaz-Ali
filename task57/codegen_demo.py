import os
import shutil
from code_alpha.codegen.schema import Edit, EditOp
from code_alpha.codegen.apply import apply_edits, EditConflict
from code_alpha.codegen.style import detect_style
from code_alpha.codegen.boilerplate import generate_boilerplate
from code_alpha.codegen.lint import run_formatters

REPO_ROOT = "codegen_demo_repo"
shutil.rmtree(REPO_ROOT, ignore_errors=True)
os.makedirs(REPO_ROOT)

EXISTING_FILE = os.path.join(REPO_ROOT, "auth.py")
with open(EXISTING_FILE, "w") as f:
    f.write(
        'import os\n'
        'import hashlib\n'
        '\n'
        'def hash_password(password):\n'
        '    return hashlib.sha256(password.encode()).hexdigest()\n'
        '\n'
        'def check_password(password, hashed):\n'
        '    return hash_password(password) == hashed\n'
    )

if __name__ == "__main__":
    print("== 1. detect_style() on the existing file ==")
    with open(EXISTING_FILE) as f:
        source = f.read()
    style = detect_style([source])
    print(f"  {style}")

    print("\n== 2. structured multi-file edit: replace a function + create a new file ==")
    old_lines = source.splitlines(keepends=True)
    old_range = "".join(old_lines[3:5])  # the hash_password function, lines 4-5

    replace_edit = Edit(
        op=EditOp.REPLACE, file_path=EXISTING_FILE, start_line=4, end_line=5,
        new_content=(
            "def hash_password(password, salt=None):\n"
            "    salt = salt or os.urandom(16).hex()\n"
            "    return hashlib.sha256((salt + password).encode()).hexdigest(), salt\n"
        ),
        expected_old_content=old_range,
    )

    boilerplate = generate_boilerplate(
        file_path=os.path.join(REPO_ROOT, "rate_limit.py"),
        purpose="Rate limiting middleware for auth endpoints.",
        style=style,
        imports=["import time", "", "from collections import defaultdict"],
    )
    create_edit = Edit(
        op=EditOp.CREATE, file_path=os.path.join(REPO_ROOT, "rate_limit.py"),
        new_content=boilerplate + "\n_hits = defaultdict(list)\n",
    )

    results = apply_edits([replace_edit, create_edit])
    for r in results:
        print(f"  {r.op.value:8s} {r.file_path}: applied={r.applied} error={r.error}")

    print("\n== 3. verify content on disk ==")
    with open(EXISTING_FILE) as f:
        print("  auth.py now:\n" + "".join(f"    {l}" for l in f.readlines()))
    with open(os.path.join(REPO_ROOT, "rate_limit.py")) as f:
        print("  rate_limit.py:\n" + "".join(f"    {l}" for l in f.readlines()))

    print("== 4. conflict detection: apply same edit again with stale expected_old_content ==")
    try:
        apply_edits([replace_edit])  # expected_old_content no longer matches — file already changed
    except EditConflict as e:
        print(f"  correctly rejected: {str(e).splitlines()[0]}")

    print("\n== 5. run real formatter (black) on touched files ==")
    lint_results = run_formatters([EXISTING_FILE, os.path.join(REPO_ROOT, "rate_limit.py")])
    for lr in lint_results:
        print(f"  {lr.file_path}: tool={lr.tool} ran={lr.ran}")

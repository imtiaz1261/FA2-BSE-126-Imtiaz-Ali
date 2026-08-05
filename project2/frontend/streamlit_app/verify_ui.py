"""Quick import check for all redesigned frontend files."""
import sys; sys.path.insert(0,'.')

errors = []
def chk(label, fn):
    try:
        fn()
        print(f"  OK  {label}")
    except Exception as e:
        errors.append((label, str(e)))
        print(f"  FAIL {label}: {e}")

chk("theme",         lambda: __import__("theme"))
chk("ui_components", lambda: __import__("ui_components"))
chk("auth_forms",    lambda: __import__("components.auth_forms", fromlist=["render_auth_gate"]))
chk("chat",          lambda: __import__("components.chat",       fromlist=["render_chat"]))
chk("research",      lambda: __import__("components.research",   fromlist=["render_research"]))
chk("documents",     lambda: __import__("components.documents",  fromlist=["render_document_manager"]))
chk("sidebar",       lambda: __import__("components.sidebar",    fromlist=["render_sidebar"]))

print()
if errors:
    print(f"FAILED ({len(errors)} errors):")
    for lbl,msg in errors:
        print(f"  {lbl}: {msg}")
    sys.exit(1)
else:
    print("ALL UI IMPORTS: PASS")
    sys.exit(0)

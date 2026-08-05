"""Quick smoke-test for Phase 13/14/15 imports."""
import sys
sys.path.insert(0, ".")

errors = []

def chk(label, fn):
    try:
        fn()
        print(f"  OK  {label}")
    except Exception as e:
        errors.append((label, str(e)))
        print(f"  FAIL {label}: {e}")

chk("P13 research_service",
    lambda: __import__("app.services.research_service", fromlist=["run_research"]))

chk("P13 research router",
    lambda: __import__("app.api.research", fromlist=["router"]))

chk("P14 input_guard",
    lambda: __import__("app.guardrails.input_guard", fromlist=["check_input"]))

chk("P14 output_guard",
    lambda: __import__("app.guardrails.output_guard", fromlist=["check_output"]))

chk("P14 rag_guard",
    lambda: __import__("app.guardrails.rag_guard", fromlist=["sanitise_chunks"]))

chk("P14 security_service",
    lambda: __import__("app.services.security_service", fromlist=["log_security_event"]))

chk("P14 SecurityEvent model",
    lambda: __import__("app.models.security_event", fromlist=["SecurityEvent"]))

chk("P15 subscription_service",
    lambda: __import__("app.services.subscription_service", fromlist=["check_quota"]))

chk("P15 subscription router",
    lambda: __import__("app.api.subscription", fromlist=["subscription_router"]))

chk("P13/14/15 main app",
    lambda: __import__("app.main", fromlist=["app"]))

def check_routes():
    from app.main import app
    routes = [r.path for r in app.routes]
    required = [
        "/api/research/run",
        "/api/research/stream",
        "/api/subscription/me",
        "/api/subscription/upgrade",
        "/api/usage/me",
        "/api/admin/analytics/security/summary",
    ]
    missing = [r for r in required if not any(r in path for path in routes)]
    if missing:
        raise AssertionError(f"Missing routes: {missing}")

chk("All required routes registered", check_routes)

print()
if errors:
    print(f"FAILED: {len(errors)} errors")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
    sys.exit(0)

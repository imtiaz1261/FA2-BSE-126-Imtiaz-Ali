from code_alpha.context.engine import ContextEngine
from code_alpha.context.tools import dispatch, TOOL_DEFINITIONS

if __name__ == "__main__":
    engine = ContextEngine(root="code_alpha")
    n = engine.index_repo()
    print(f"indexed {n} files\n")

    print("== search_code('run tests in sandbox') ==")
    for hit in dispatch(engine, "search_code", {"query": "run tests in sandbox", "top_k": 3}):
        print(f"  {hit['score']:.3f}  {hit['file']}::{hit['symbol_name']}")

    print("\n== find_usages('transition') ==")
    usages = dispatch(engine, "find_usages", {"symbol": "transition"})
    print(f"  definitions: {usages['definitions']}")
    print(f"  call_sites: {usages['call_sites']}")

    print("\n== get_dependency_graph() (sample) ==")
    graph = dispatch(engine, "get_dependency_graph", {})
    for f, deps in list(graph.items())[:3]:
        print(f"  {f} -> {deps}")

    print(f"\n{len(TOOL_DEFINITIONS)} tools registered: {[t['name'] for t in TOOL_DEFINITIONS]}")

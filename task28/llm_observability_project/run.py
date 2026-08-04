"""
Convenience helper — prints the commands needed to run this project.
Actually starting FastAPI and Streamlit in this same process isn't practical
(they're two long-running servers), so this just prints the commands
you run in two separate terminals.
"""


def main():
    print("Start each service in its own terminal:\n")
    print("  1) API server:")
    print("     uvicorn app.main:app --reload\n")
    print("  2) Dashboard:")
    print("     streamlit run dashboard/streamlit_app.py\n")
    print("Optional — run the test suite:")
    print("     pytest\n")
    print("Optional — run the benchmark directly (no UI):")
    print("     python -c \"from benchmark.runner import run_benchmark; "
          "from benchmark.evaluator import export_report; "
          "r = run_benchmark(['baseline','caching','prompt_optimization','full'], 2); "
          "export_report(r, 'markdown'); print(r)\"")


if __name__ == "__main__":
    main()

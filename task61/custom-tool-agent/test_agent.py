"""
test_agent.py
--------------
Runs the agent against a mix of queries -- some that SHOULD trigger
the unit_converter tool, some that clearly SHOULDN'T -- and checks
whether the agent's actual behavior matches expectation, using
`return_intermediate_steps` to see if a tool call actually happened.

Usage:
    python test_agent.py
"""

import sys

from agent import build_agent_executor, AgentInitError

# (query, expect_tool_call)
TEST_CASES = [
    ("Convert 10 kilometers to miles.", True),
    ("What is 98.6 fahrenheit in celsius?", True),
    ("How much is 5 kg in pounds?", True),
    ("Convert 100 cm to inches please.", True),
    ("What's the capital of France?", False),
    ("Tell me a short joke.", False),
    ("Who wrote Romeo and Juliet?", False),
    ("What's your favorite color?", False),
]


def _tool_was_called(result: dict) -> bool:
    steps = result.get("intermediate_steps", [])
    return len(steps) > 0


def _print_table(rows: list) -> None:
    headers = ("Query", "Expected", "Actual", "Result")
    col_widths = [
        max(len(headers[0]), *(len(r[0]) for r in rows)),
        max(len(headers[1]), *(len(r[1]) for r in rows)),
        max(len(headers[2]), *(len(r[2]) for r in rows)),
        max(len(headers[3]), *(len(r[3]) for r in rows)),
    ]

    def fmt_row(a, b, c, d):
        return f"| {a.ljust(col_widths[0])} | {b.ljust(col_widths[1])} | {c.ljust(col_widths[2])} | {d.ljust(col_widths[3])} |"

    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    print(sep)
    print(fmt_row(*headers))
    print(sep)
    for row in rows:
        print(fmt_row(*row))
    print(sep)


def main() -> int:
    try:
        executor = build_agent_executor()
    except AgentInitError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Running {len(TEST_CASES)} test case(s) against the agent...\n")

    rows = []
    passed = 0
    for query, expected in TEST_CASES:
        try:
            result = executor.invoke({"input": query})
            actual = _tool_was_called(result)
        except Exception as exc:
            print(f"  ! Query failed to run: {query!r} -> {exc}")
            actual = None

        is_pass = actual == expected
        passed += int(is_pass)

        rows.append((
            (query[:45] + "...") if len(query) > 48 else query,
            "Tool call" if expected else "No tool",
            "Tool call" if actual else ("No tool" if actual is not None else "ERROR"),
            "PASS" if is_pass else "FAIL",
        ))

    print()
    _print_table(rows)
    print(f"\n{passed}/{len(TEST_CASES)} test case(s) passed.")

    return 0 if passed == len(TEST_CASES) else 1


if __name__ == "__main__":
    sys.exit(main())

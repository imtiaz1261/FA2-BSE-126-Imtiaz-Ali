"""The Fixer's two-step prompt. Step 1 forces explicit root-cause reasoning
*before* any patch is proposed — this is the guard against blind-guess
fixes: a patch that isn't grounded in a stated cause is easy to spot as
wrong, either by the loop's next test run or by a human reviewing the log."""

ROOT_CAUSE_PROMPT = """You are the Fixer agent, diagnosing a test failure.
Do not propose a fix yet — only explain the root cause.

Task: {task_description}
Fix attempt {attempt} of {max_attempts}.

Failing test: {test_name}
File: {file}  Line: {line}

Stack trace:
---
{stack_trace}
---

Expected: {expected}
Actual: {actual}

Relevant source (the function(s) under test, from the Context Engine):
---
{source_context}
---

{prior_attempts_note}

Explain, in a few sentences:
1. What the test expected vs. what actually happened.
2. The specific line(s) of source code responsible.
3. Why that code produces the observed behavior (not just "it's wrong" —
   trace the actual logic).

If you cannot identify a concrete root cause from the evidence above, say so
explicitly — do not fabricate a plausible-sounding explanation. Output only
the diagnosis, no patch."""


PATCH_PROMPT = """You are the Fixer agent. You just diagnosed this failure:
---
{diagnosis}
---

Propose the smallest possible patch that addresses exactly that root cause —
not a rewrite, not unrelated cleanup, not a defensive fix for a different
failure mode you're speculating about.

Output a JSON array of edits in this schema (same as Module 5's structured
edits — replace/insert only, never a full-file rewrite unless the diagnosis
shows the entire file's logic is wrong):
{{
  "op": "replace" | "insert",
  "file_path": "...",
  "start_line": <int>,
  "end_line": <int, only for replace>,
  "new_content": "...",
  "expected_old_content": "<verbatim current content of this range>"
}}

Output only the JSON array, no prose."""


PRIOR_ATTEMPTS_TEMPLATE = """Prior attempts on this same failure (do not repeat
a diagnosis or patch already tried and shown not to work):
{prior_summary}"""

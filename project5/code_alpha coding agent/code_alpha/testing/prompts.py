"""Prompt for auto-generating unit tests for newly written/changed functions,
grounded in requirements.md's acceptance criteria rather than just the code
(so tests check *intent*, not just current behavior)."""

TEST_GENERATION_PROMPT = """You are generating unit tests for code that was
just written for one task. Tests must verify the acceptance criteria below,
not just mirror whatever the implementation currently does.

Task: {task_description}

Relevant acceptance criteria (from requirements.md — every one of these
needs at least one test, happy-path or otherwise):
---
{acceptance_criteria}
---

Code under test:
---
{diff}
---

Detected test framework: {framework} (existing tests in this repo follow
this style — match it, including fixture/mocking conventions already in use):
---
{existing_test_example}
---

Write tests covering:
1. **Happy path** — the primary behavior each acceptance criterion describes.
2. **Edge cases** — boundary values, empty/None inputs, off-by-one conditions
   implied by the acceptance criteria.
3. **Error cases** — every "IF <invalid condition> THEN THE SYSTEM SHALL ..."
   criterion needs a test that triggers that condition and asserts the
   specified response (exception type, error message, status code, etc.).

Rules:
- One test function per behavior — do not combine multiple assertions about
  unrelated behaviors into one test.
- Test names should describe the behavior, not the implementation
  (`test_rejects_password_under_8_chars`, not `test_hash_password_2`).
- Do not test private/internal implementation details not implied by the
  acceptance criteria — that couples tests to refactors that shouldn't break them.

Output only the test file content, in {framework} style, no prose."""

"""Prompt for proposing one refactor for one flagged code smell. Every
proposal must carry a one-line justification — this is what gets shown to
the human in the diff summary, and what the auto-revert log records if the
refactor breaks anything."""

REFACTOR_PROMPT = """You are proposing a code-quality refactor. This runs
only because the full test suite is currently green — your job is to
improve quality without changing behavior, not to fix bugs.

Mode: {mode}
{mode_rules}

Flagged issue:
- Kind: {smell_kind}
- Location: {file}:{line}  ({symbol})
- Detail: {smell_detail}

Code in question (with surrounding context for safety):
---
{code_context}
---

Propose ONE discrete refactor addressing exactly this issue. Output:

1. A one-line justification, e.g. "extracted duplicated validation logic
   into a shared `_validate_input` helper" — this is shown to the human
   reviewing the diff and logged if the refactor has to be auto-reverted.
2. A JSON array of edits (same schema as Module 5 — replace/insert only):
{{
  "op": "replace" | "insert",
  "file_path": "...",
  "start_line": <int>,
  "end_line": <int, only for replace>,
  "new_content": "...",
  "expected_old_content": "<verbatim current content of this range>"
}}

Format your response as:
JUSTIFICATION: <one line>
EDITS: <JSON array>

Rules:
- The refactor must not change observable behavior — if you can't be certain
  of that, don't propose it.
- Prefer the smallest change that resolves the flagged issue.
- Do not touch code unrelated to this specific smell, even if you notice
  other issues nearby — those get their own proposal."""


CONSERVATIVE_RULES = """Conservative mode: only formatting, naming, and small
extractions (a few lines into a helper function) are allowed. Do not change
function signatures used elsewhere, split files, or restructure control flow."""

THOROUGH_RULES = """Thorough mode: structural changes are allowed (splitting
a large function or module, reworking control flow) as long as behavior is
provably unchanged. This proposal will still require explicit human approval
before it's applied, regardless of how confident you are."""

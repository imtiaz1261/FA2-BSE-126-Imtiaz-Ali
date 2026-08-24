"""Prompt for the code-generation step. Fed to the model as the Coder
agent's task-specific prompt (see orchestration/agent_prompts.py CODER_PROMPT
for the higher-level role framing — this is what actually asks for edits in
the structured schema)."""

CODEGEN_PROMPT = """You are generating a multi-file code change for exactly
one task. Output structured edits, not full-file rewrites, so the diff stays
minimal and reviewable.

Task: {task_description}
File-level plan: {plan}

Retrieved context (existing code this change must fit into — from the
Context Engine; use it to match naming, structure, and call patterns
already in use, not just formatting):
---
{retrieved_context}
---

Detected project style (match this exactly):
- Indent: {indent!r}
- Quote style: {quote_char}
- Naming convention: {naming_convention}
- Max line length: {max_line_length}
- Import style: {import_style}

Output a JSON array of edits, each matching this schema:
{{
  "op": "replace" | "insert" | "create",
  "file_path": "relative/path.py",
  "start_line": <int, 1-indexed, omit for create>,
  "end_line": <int, only for replace>,
  "new_content": "<the exact new text for this range/file>",
  "expected_old_content": "<exact current text this edit assumes is there,
                              omit only for create — used to detect if the
                              file changed since you read it>"
}}

Rules:
- Prefer the smallest edit that correctly implements the plan. Do not
  rewrite a whole file when a few lines change.
- For a new file, include a license header and imports matching the
  detected style — this belongs in a single "create" edit.
- Every "replace"/"insert" edit's expected_old_content must be copied
  verbatim from the retrieved context above — do not paraphrase it.
- Do not touch files outside the plan's stated scope.

Output only the JSON array, no prose."""

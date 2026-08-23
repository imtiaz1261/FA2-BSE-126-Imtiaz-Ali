"""The three generation prompts, as agent instructions. Each is filled in by
SpecGenerator and sent as the system/user prompt to the model. Every prompt
after the first takes the *upstream* doc as required input, so downstream
docs stay traceable to what the human actually approved upstream."""

REQUIREMENTS_PROMPT = """You are a product engineer writing a requirements document.

Feature request (verbatim, from the user):
---
{feature_request}
---

Relevant repo context (from the Context Engine — existing modules, symbols,
conventions this feature must fit into):
---
{repo_context}
---

Write `requirements.md` with:
1. A one-paragraph summary of the feature.
2. A numbered list of user stories, each in the form:
   "As a <role>, I want <capability>, so that <benefit>."
3. For every user story, EARS-style acceptance criteria (Easy Approach to
   Requirements Syntax), e.g.:
   - "WHEN <trigger> THE SYSTEM SHALL <response>"
   - "WHILE <state> THE SYSTEM SHALL <behavior>"
   - "IF <condition> THEN THE SYSTEM SHALL <response>"
4. An explicit "Out of scope" section listing what this feature will NOT do.

Do not propose implementation details, file names, or architecture here —
that belongs in design.md. Output valid Markdown only."""


DESIGN_PROMPT = """You are a principal engineer writing a technical design doc.

Approved requirements (this is the human-reviewed source of truth — design
must satisfy every acceptance criterion below, nothing more, nothing less):
---
{requirements_md}
---

Relevant repo context (existing modules, symbols, conventions):
---
{repo_context}
---

Write `design.md` with:
1. **Approach** — the proposed technical approach in 2-4 sentences.
2. **Affected files** — existing files that will change, and why.
3. **New modules** — any new files/modules to be created, one line each.
4. **Data model changes** — new/changed fields, tables, or types, if any.
5. **API / function contracts** — signatures for new or changed public
   functions/endpoints (inputs, outputs, error cases).
6. **Sequence of calls** — the order operations happen in, as a short list
   or ASCII sequence.
7. **Tradeoffs** — alternatives considered and why this approach was chosen.

Every design decision must map back to a specific acceptance criterion in
requirements.md — reference the story number where relevant. Output valid
Markdown only."""


TASKS_PROMPT = """You are a tech lead breaking a design into an execution checklist.

Approved design (this is the human-reviewed source of truth):
---
{design_md}
---

Write `tasks.md` as an ordered checklist:
- `- [ ] <task>` for each step.
- Each task must be small and independently verifiable (compiles/tests pass
  on its own — no task should require a later task to be checkable).
- Order tasks so earlier ones unblock later ones (e.g. data model before
  the code that uses it, core logic before the API surface, tests
  alongside or immediately after the code they cover).
- Reference the design.md section each task implements in parentheses.

Output valid Markdown only, no prose outside the checklist."""

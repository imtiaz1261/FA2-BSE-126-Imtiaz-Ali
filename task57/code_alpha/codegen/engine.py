import json
from typing import Callable, Optional
from .schema import Edit, EditOp
from .style import StyleProfile, detect_style
from .prompts import CODEGEN_PROMPT
from .apply import apply_edits, ApplyResult
from .lint import run_formatters, LintResult

Completer = Callable[[str], str]


def _stub_completer(prompt: str) -> str:
    """Offline stand-in — real deployment sends `prompt` to the Messages API
    and parses its JSON edit-array response the same way `generate_edits`
    does below."""
    return "[]"


class CodeGenEngine:
    def __init__(self, completer: Optional[Completer] = None):
        self.complete = completer or _stub_completer

    def generate_edits(
        self,
        task_description: str,
        plan: str,
        retrieved_context: str,
        style: StyleProfile,
    ) -> list[Edit]:
        prompt = CODEGEN_PROMPT.format(
            task_description=task_description, plan=plan,
            retrieved_context=retrieved_context,
            indent=style.indent, quote_char=style.quote_char,
            naming_convention=style.naming_convention,
            max_line_length=style.max_line_length, import_style=style.import_style,
        )
        raw = self.complete(prompt)
        try:
            items = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"model did not return valid edit JSON: {e}\nraw: {raw[:200]}")

        edits = []
        for item in items:
            edits.append(Edit(
                op=EditOp(item["op"]), file_path=item["file_path"],
                new_content=item["new_content"],
                start_line=item.get("start_line"), end_line=item.get("end_line"),
                expected_old_content=item.get("expected_old_content"),
            ))
        return edits

    def apply(self, edits: list[Edit]) -> list[ApplyResult]:
        return apply_edits(edits)

    def lint(self, touched_files: list[str]) -> list[LintResult]:
        return run_formatters(touched_files)

    def run(
        self, task_description: str, plan: str, retrieved_context: str, source_files: list[str],
    ) -> tuple[list[ApplyResult], list[LintResult]]:
        """Full pass: detect style -> generate edits -> apply -> format touched files."""
        style = detect_style(source_files)
        edits = self.generate_edits(task_description, plan, retrieved_context, style)
        apply_results = self.apply(edits)
        touched = sorted({r.file_path for r in apply_results if r.applied})
        lint_results = self.lint(touched)
        return apply_results, lint_results

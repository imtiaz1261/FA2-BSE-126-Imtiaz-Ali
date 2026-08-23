from typing import Callable, Optional
from .prompts import REQUIREMENTS_PROMPT, DESIGN_PROMPT, TASKS_PROMPT
from .store import SpecStore, DOC_ORDER


# Swap this for a real call to the Anthropic Messages API
# (model="claude-sonnet-4-6", the filled prompt as the user message).
# Kept as a pluggable function so the module is testable without a live API.
Completer = Callable[[str], str]


def _stub_completer(prompt: str) -> str:
    """Deterministic offline stand-in so the pipeline is runnable without
    an API key. Replace with a real Messages API call in production."""
    if "EARS-style" in prompt:
        return ("# Requirements\n\n(stub) Generated from the feature request "
                "and repo context above — replace `_stub_completer` with a "
                "real model call to get actual user stories + acceptance criteria.")
    if "design.md" in prompt.split("\n")[0] or "Affected files" in prompt:
        return "# Design\n\n(stub) Generated from the approved requirements above."
    return "# Tasks\n\n- [ ] (stub) Generated from the approved design above."


class SpecGenerator:
    def __init__(self, repo_root: str, feature_slug: str, completer: Optional[Completer] = None):
        self.store = SpecStore(repo_root, feature_slug)
        self.complete = completer or _stub_completer

    # -- generation steps ---------------------------------------------------

    def generate_requirements(self, feature_request: str, repo_context: str) -> str:
        prompt = REQUIREMENTS_PROMPT.format(
            feature_request=feature_request, repo_context=repo_context)
        content = self.complete(prompt)
        self.store.write_doc("requirements", content)
        return content

    def generate_design(self, repo_context: str) -> str:
        requirements_md = self.store.read_doc("requirements")
        if requirements_md is None:
            raise ValueError("requirements.md must exist before generating design.md")
        prompt = DESIGN_PROMPT.format(requirements_md=requirements_md, repo_context=repo_context)
        content = self.complete(prompt)
        self.store.write_doc("design", content)
        return content

    def generate_tasks(self) -> str:
        design_md = self.store.read_doc("design")
        if design_md is None:
            raise ValueError("design.md must exist before generating tasks.md")
        prompt = TASKS_PROMPT.format(design_md=design_md)
        content = self.complete(prompt)
        self.store.write_doc("tasks", content)
        return content

    def generate_all(self, feature_request: str, repo_context: str) -> dict[str, str]:
        return {
            "requirements": self.generate_requirements(feature_request, repo_context),
            "design": self.generate_design(repo_context),
            "tasks": self.generate_tasks(),
        }

    # -- regeneration after a human edit -------------------------------------

    def regenerate_from(self, doc_name: str, feature_request: str = "", repo_context: str = "") -> list[str]:
        """Call after the human hand-edits `doc_name` (or any upstream doc).
        Regenerates every doc downstream of it that is now stale, in order,
        so the whole chain stays consistent. Returns the list of docs regenerated."""
        if doc_name not in DOC_ORDER:
            raise ValueError(f"unknown doc: {doc_name}")

        regenerated = []
        start = DOC_ORDER.index(doc_name)
        # doc_name itself was hand-edited, so everything after it is now stale
        # relative to that edit; regenerate each downstream doc in order.
        for name in DOC_ORDER[start + 1:]:
            if name == "design":
                self.generate_design(repo_context)
            elif name == "tasks":
                self.generate_tasks()
            regenerated.append(name)
        return regenerated

    def sync_status(self) -> dict[str, bool]:
        """{doc_name: is_stale} for every doc — surfaced to the human before
        they proceed, so nothing generates from an out-of-date upstream silently."""
        return {name: self.store.is_stale(name) for name in DOC_ORDER}

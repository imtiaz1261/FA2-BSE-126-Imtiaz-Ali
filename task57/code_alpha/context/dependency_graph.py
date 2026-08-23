import os
from .parser import FileParse


def _resolve_python_import(root: str, module: str, all_files: set[str]) -> str | None:
    candidate = os.path.join(root, *module.split(".")) + ".py"
    return candidate if candidate in all_files else None


class DependencyGraph:
    """file -> set of files it imports (resolved where possible, else raw module name)."""

    def __init__(self):
        self._graph: dict[str, set[str]] = {}

    def add_file(self, root: str, parsed: FileParse, all_files: set[str]) -> None:
        resolved = set()
        for imp in parsed.imports:
            if parsed.language == "python":
                target = _resolve_python_import(root, imp, all_files)
                resolved.add(target or f"external:{imp}")
            else:
                # relative JS/TS import -> best-effort local file match
                match = next((f for f in all_files if imp.strip("./") in f), None)
                resolved.add(match or f"external:{imp}")
        self._graph[parsed.file] = resolved

    def remove_file(self, file: str) -> None:
        self._graph.pop(file, None)

    def as_dict(self) -> dict[str, list[str]]:
        return {f: sorted(deps) for f, deps in self._graph.items()}

import ast
import re
from dataclasses import dataclass, field
from typing import List

try:
    import tree_sitter_languages  # optional, used for non-python langs if installed
    _HAS_TREE_SITTER = True
except ImportError:
    _HAS_TREE_SITTER = False


@dataclass
class Symbol:
    name: str
    kind: str          # "function" | "class"
    file: str
    start_line: int
    end_line: int
    calls: List[str] = field(default_factory=list)
    docstring: str = ""


@dataclass
class FileParse:
    file: str
    language: str
    imports: List[str] = field(default_factory=list)
    symbols: List[Symbol] = field(default_factory=list)
    source: str = ""


def _parse_python(path: str, source: str) -> FileParse:
    tree = ast.parse(source, filename=path)
    imports, symbols = [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            calls = [
                n.func.id for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            symbols.append(Symbol(
                name=node.name,
                kind="function" if not isinstance(node, ast.ClassDef) else "class",
                file=path,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                calls=calls,
                docstring=ast.get_docstring(node) or "",
            ))
    return FileParse(file=path, language="python", imports=imports, symbols=symbols, source=source)


# --- Regex fallback for languages without a wired-up tree-sitter grammar ---
# Best-effort: good enough for chunking/indexing, not a full parser.
_FUNC_RE = re.compile(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>|(\w+)\s*\([^)]*\)\s*\{)")
_CLASS_RE = re.compile(r"class\s+(\w+)")
_IMPORT_RE = re.compile(r"(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))")


def _parse_generic(path: str, source: str, language: str) -> FileParse:
    imports = [a or b for a, b in _IMPORT_RE.findall(source)]
    lines = source.splitlines()
    symbols = []

    for i, line in enumerate(lines, start=1):
        m = _CLASS_RE.search(line)
        if m:
            symbols.append(Symbol(name=m.group(1), kind="class", file=path, start_line=i, end_line=i))
            continue
        m = _FUNC_RE.search(line)
        if m:
            name = next(g for g in m.groups() if g)
            symbols.append(Symbol(name=name, kind="function", file=path, start_line=i, end_line=i))

    return FileParse(file=path, language=language, imports=imports, symbols=symbols, source=source)


def parse_file(path: str, language: str) -> FileParse:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        source = f.read()
    if language == "python":
        try:
            return _parse_python(path, source)
        except SyntaxError:
            pass  # fall through to generic best-effort parse
    return _parse_generic(path, source, language)

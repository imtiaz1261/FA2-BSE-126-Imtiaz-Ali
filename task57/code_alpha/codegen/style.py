import re
from collections import Counter
from dataclasses import dataclass

_DOUBLE_Q = re.compile(r'"')
_SINGLE_Q = re.compile(r"'")
_INDENT_RE = re.compile(r"^( +|\t+)\S", re.MULTILINE)
_SNAKE_DEF = re.compile(r"^def ([a-z_][a-z0-9_]*)\(", re.MULTILINE)
_CAMEL_DEF = re.compile(r"^def ([a-z]+[A-Z][a-zA-Z0-9]*)\(", re.MULTILINE)
_IMPORT_LINE = re.compile(r"^(import |from )", re.MULTILINE)


@dataclass
class StyleProfile:
    indent: str              # "    " (4-space), "  " (2-space), or "\t"
    quote_char: str           # '"' or "'"
    naming_convention: str    # "snake_case" or "camelCase"
    max_line_length: int
    import_style: str         # "grouped" (stdlib/third-party/local blocks) or "flat"


def detect_style(source_files: list[str]) -> StyleProfile:
    """Analyzes concatenated source (already-loaded file contents, e.g. from
    the Context Engine) and returns the dominant conventions. Falls back to
    sane defaults (PEP 8-ish) when a file is too short/empty to tell."""
    text = "\n".join(source_files)
    if not text.strip():
        return StyleProfile("    ", '"', "snake_case", 88, "grouped")

    indents = _INDENT_RE.findall(text)
    indent_counter = Counter(
        "\t" if i.startswith("\t") else (" " * (len(i) if len(i) in (2, 4) else 4))
        for i in indents
    )
    indent = indent_counter.most_common(1)[0][0] if indent_counter else "    "

    dq, sq = len(_DOUBLE_Q.findall(text)), len(_SINGLE_Q.findall(text))
    quote_char = '"' if dq >= sq else "'"

    snake, camel = len(_SNAKE_DEF.findall(text)), len(_CAMEL_DEF.findall(text))
    naming = "snake_case" if snake >= camel else "camelCase"

    lines = text.splitlines()
    lengths = [len(l) for l in lines if l.strip()]
    max_line_length = 100 if lengths and max(lengths) > 88 else 88

    import_lines = [l for l in lines if _IMPORT_LINE.match(l)]
    blank_between_imports = any(
        lines[i].strip() == "" for i in range(len(lines) - 1)
        if _IMPORT_LINE.match(lines[i]) is None and i > 0 and _IMPORT_LINE.match(lines[i - 1])
    )
    import_style = "grouped" if (import_lines and blank_between_imports) else "flat"

    return StyleProfile(indent, quote_char, naming, max_line_length, import_style)

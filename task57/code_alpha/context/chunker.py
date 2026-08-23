from dataclasses import dataclass
from .parser import FileParse


@dataclass
class Chunk:
    id: str
    file: str
    symbol_name: str
    kind: str
    start_line: int
    end_line: int
    text: str


def chunk_file(parsed: FileParse) -> list[Chunk]:
    """One chunk per function/class. Falls back to a whole-file chunk
    if no symbols were found (e.g. config files, scripts)."""
    lines = parsed.source.splitlines()
    if not parsed.symbols:
        return [Chunk(
            id=f"{parsed.file}::__file__",
            file=parsed.file, symbol_name="__file__", kind="file",
            start_line=1, end_line=len(lines),
            text=parsed.source,
        )]

    chunks = []
    for sym in parsed.symbols:
        start, end = max(sym.start_line - 1, 0), min(sym.end_line, len(lines))
        text = "\n".join(lines[start:end]) or sym.name
        chunks.append(Chunk(
            id=f"{parsed.file}::{sym.name}:{sym.start_line}",
            file=parsed.file, symbol_name=sym.name, kind=sym.kind,
            start_line=sym.start_line, end_line=sym.end_line, text=text,
        ))
    return chunks

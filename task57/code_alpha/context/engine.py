import os
from .scanner import walk_repo, detect_language
from .parser import parse_file, FileParse, Symbol
from .chunker import chunk_file
from .embeddings import HashEmbedder
from .vector_store import InMemoryVectorStore
from .dependency_graph import DependencyGraph
from .watcher import make_watcher


class ContextEngine:
    """Repo indexing + symbol-level and semantic retrieval for one repository.
    One instance per repo (mirrors the per-repo scoping in the vector DB schema)."""

    def __init__(self, root: str, embedder=None, vector_store=None):
        self.root = os.path.abspath(root)
        self.embedder = embedder or HashEmbedder()
        self.store = vector_store or InMemoryVectorStore()
        self.dep_graph = DependencyGraph()
        self._parsed: dict[str, FileParse] = {}          # file -> FileParse
        self._symbol_index: dict[str, list[Symbol]] = {}  # symbol name -> [Symbol, ...]
        self._watcher = None

    # -- indexing ----------------------------------------------------------

    def index_repo(self) -> int:
        files = set(walk_repo(self.root))
        for path in files:
            self._index_file(path, files)
        return len(files)

    def _index_file(self, path: str, all_files: set[str]) -> None:
        language = detect_language(path)
        try:
            parsed = parse_file(path, language)
        except (OSError, UnicodeDecodeError):
            return

        self._deindex_file(path)
        self._parsed[path] = parsed
        self.dep_graph.add_file(self.root, parsed, all_files)

        for sym in parsed.symbols:
            self._symbol_index.setdefault(sym.name, []).append(sym)

        for chunk in chunk_file(parsed):
            vector = self.embedder.embed(chunk.text)
            self.store.upsert(chunk.id, vector, {
                "file": chunk.file, "symbol_name": chunk.symbol_name,
                "kind": chunk.kind, "start_line": chunk.start_line,
                "end_line": chunk.end_line, "text": chunk.text,
            })

    def _deindex_file(self, path: str) -> None:
        old = self._parsed.pop(path, None)
        if old:
            for sym in old.symbols:
                self._symbol_index[sym.name] = [
                    s for s in self._symbol_index.get(sym.name, []) if s.file != path
                ]
        self.store.delete_by_file(path)
        self.dep_graph.remove_file(path)

    def reindex_file(self, path: str, deleted: bool = False) -> None:
        """Called by the file watcher — re-indexes only the changed file."""
        if deleted or not os.path.exists(path):
            self._deindex_file(path)
            return
        all_files = set(walk_repo(self.root))
        self._index_file(path, all_files)

    def start_watching(self) -> None:
        self._watcher = make_watcher(self.root, self.reindex_file)
        self._watcher.start()

    def stop_watching(self) -> None:
        if self._watcher:
            self._watcher.stop()

    # -- retrieval tools (agent-facing) -------------------------------------

    def search_code(self, query: str, top_k: int = 5) -> list[dict]:
        vector = self.embedder.embed(query)
        hits = self.store.search(vector, top_k=top_k)
        return [{"score": round(h.score, 4), **h.metadata} for h in hits]

    def find_usages(self, symbol: str) -> list[dict]:
        results = []
        for parsed in self._parsed.values():
            for sym in parsed.symbols:
                if symbol in sym.calls:
                    results.append({
                        "caller": sym.name, "file": sym.file,
                        "line": sym.start_line,
                    })
        definitions = [
            {"file": s.file, "line": s.start_line, "kind": s.kind}
            for s in self._symbol_index.get(symbol, [])
        ]
        return {"definitions": definitions, "call_sites": results}

    def get_file(self, path: str) -> str:
        abspath = path if os.path.isabs(path) else os.path.join(self.root, path)
        parsed = self._parsed.get(abspath)
        if parsed:
            return parsed.source
        with open(abspath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def get_dependency_graph(self) -> dict[str, list[str]]:
        return self.dep_graph.as_dict()

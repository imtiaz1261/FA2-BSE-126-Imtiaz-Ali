import hashlib
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

DOC_ORDER = ["requirements", "design", "tasks"]
UPSTREAM = {"requirements": None, "design": "requirements", "tasks": "design"}
FILENAMES = {d: f"{d}.md" for d in DOC_ORDER}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


@dataclass
class DocMeta:
    version: int
    hash: str
    generated_from_hash: Optional[str]  # hash of the upstream doc AT generation time


class SpecStore:
    """Manages requirements.md / design.md / tasks.md for one feature under
    <repo_root>/.codealpha/specs/<slug>/ — versioned, diffable, git-reviewable.

    Layout:
      .codealpha/specs/<slug>/
        requirements.md   design.md   tasks.md      <- current (edit these)
        manifest.json                                <- hash chain
        versions/requirements.v1.md, .v2.md, ...      <- history
    """

    def __init__(self, repo_root: str, feature_slug: str):
        self.dir = os.path.join(repo_root, ".codealpha", "specs", feature_slug)
        self.versions_dir = os.path.join(self.dir, "versions")
        self.manifest_path = os.path.join(self.dir, "manifest.json")
        os.makedirs(self.versions_dir, exist_ok=True)
        self.manifest: dict[str, dict] = self._load_manifest()

    # -- persistence ---------------------------------------------------

    def _load_manifest(self) -> dict:
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path) as f:
                return json.load(f)
        return {}

    def _save_manifest(self) -> None:
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def _doc_path(self, name: str) -> str:
        return os.path.join(self.dir, FILENAMES[name])

    # -- read/write ------------------------------------------------------

    def read_doc(self, name: str) -> Optional[str]:
        path = self._doc_path(name)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return f.read()

    def write_doc(self, name: str, content: str) -> DocMeta:
        """Writes a new current version + a timestamped/version-numbered
        snapshot, and records the hash of the upstream doc it was generated
        from (None for requirements.md, which has no upstream)."""
        prev = self.manifest.get(name, {})
        version = prev.get("version", 0) + 1

        with open(self._doc_path(name), "w") as f:
            f.write(content)
        with open(os.path.join(self.versions_dir, f"{name}.v{version}.md"), "w") as f:
            f.write(content)

        upstream_name = UPSTREAM[name]
        upstream_hash = _hash(self.read_doc(upstream_name)) if upstream_name else None

        meta = DocMeta(version=version, hash=_hash(content), generated_from_hash=upstream_hash)
        self.manifest[name] = asdict(meta)
        self._save_manifest()
        return meta

    # -- sync / staleness --------------------------------------------------

    def is_stale(self, name: str) -> bool:
        """True if `name`'s upstream doc has been hand-edited (or regenerated)
        since `name` was last generated — i.e. `name` no longer reflects it."""
        upstream_name = UPSTREAM[name]
        if upstream_name is None:
            return False
        meta = self.manifest.get(name)
        if meta is None:
            return True  # never generated
        upstream_content = self.read_doc(upstream_name)
        if upstream_content is None:
            return True
        return _hash(upstream_content) != meta["generated_from_hash"]

    def stale_chain(self, from_doc: str) -> list[str]:
        """Every doc at or after `from_doc` in DOC_ORDER that is now stale."""
        idx = DOC_ORDER.index(from_doc)
        return [d for d in DOC_ORDER[idx:] if self.is_stale(d) or d == from_doc]

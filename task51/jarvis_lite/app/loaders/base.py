"""Shared loader contract. Every format-specific loader returns the same shape."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LoadedDocument:
    """One unit of extracted text plus its provenance metadata.

    A single source file can produce multiple `LoadedDocument`s — e.g. one
    per PDF page — so downstream chunking has page-level granularity when
    it's available.
    """

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLoader(ABC):
    """Every format loader implements `load()` and nothing else."""

    @abstractmethod
    def load(self, file_path: str) -> List[LoadedDocument]:
        """Extract text from `file_path`, returning one or more LoadedDocuments."""
        raise NotImplementedError

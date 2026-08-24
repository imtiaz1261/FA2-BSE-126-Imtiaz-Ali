"""
Project Memory System for Code Alpha

Enables long-term learning of project conventions across tasks.
Persists architectural decisions, naming patterns, and design preferences.
"""

from .core import ProjectMemory, MemoryEntry, MemoryCategory
from .extraction import MemoryExtractor, ConventionExtractor
from .retrieval import MemoryRetriever, SemanticMatcher
from .storage import MemoryAdapter, MemoryManager

__all__ = [
    'ProjectMemory',
    'MemoryEntry',
    'MemoryCategory',
    'MemoryExtractor',
    'ConventionExtractor',
    'MemoryRetriever',
    'SemanticMatcher',
    'MemoryAdapter',
    'MemoryManager',
]

"""
Core project memory system for Code Alpha.

Manages persistent conventions, architectural decisions, and project-specific patterns.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)


class MemoryCategory(str, Enum):
    """Categories of project conventions and decisions."""
    
    ARCHITECTURE = "architecture"  # Architecture patterns (MVC, layered, etc.)
    NAMING = "naming"              # Naming conventions (camelCase, snake_case, etc.)
    LIBRARIES = "libraries"        # Preferred libraries and frameworks
    PATTERNS = "patterns"          # Design patterns used
    ERROR_HANDLING = "error_handling"  # Error handling strategies
    TESTING = "testing"            # Testing conventions
    CI_CD = "ci_cd"                # CI/CD pipeline patterns
    CODE_STYLE = "code_style"      # Code style preferences
    DATABASE = "database"          # Database patterns
    API = "api"                    # API design patterns
    SECURITY = "security"          # Security practices
    PERFORMANCE = "performance"    # Performance patterns
    DOCUMENTATION = "documentation"  # Documentation style
    DECISIONS = "decisions"        # Architectural decisions & rationale


@dataclass
class MemoryEntry:
    """
    A single memory entry about project conventions or decisions.
    
    Attributes:
        category: Category of this memory entry
        title: Short title of the convention
        description: Detailed description of the convention
        examples: Code examples demonstrating the convention
        rationale: Why this convention was chosen
        confidence: Confidence level (0.0-1.0) that this is actually used
        first_seen: When this pattern was first detected
        last_updated: When this memory was last updated
        human_verified: Whether a human has explicitly confirmed this
        tags: Searchable tags for semantic matching
        related_entries: IDs of related memory entries
        source_files: Files where this pattern is exemplified
    """
    
    id: str
    category: MemoryCategory
    title: str
    description: str
    examples: List[str] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 1.0
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    human_verified: bool = False
    tags: List[str] = field(default_factory=list)
    related_entries: List[str] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['category'] = self.category.value
        return data
    
    def __hash__(self):
        """Make hashable for set operations."""
        return hash(self.id)


@dataclass
class ProjectMemory:
    """
    Central repository for project conventions and decisions.
    
    Per-repository memory, isolated between projects/workspaces.
    Persists across tasks and sessions.
    """
    
    repo_root: str
    entries: Dict[str, MemoryEntry] = field(default_factory=dict)
    learned_conventions: Set[str] = field(default_factory=set)
    
    def add_entry(self, entry: MemoryEntry) -> None:
        """Add or update a memory entry."""
        self.entries[entry.id] = entry
        self.learned_conventions.add(entry.title)
        logger.info(f"Added memory entry: {entry.title}")
    
    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        return self.entries.get(entry_id)
    
    def get_by_category(self, category: MemoryCategory) -> List[MemoryEntry]:
        """Get all entries in a category."""
        return [
            entry for entry in self.entries.values()
            if entry.category == category
        ]
    
    def get_by_tags(self, tags: List[str]) -> List[MemoryEntry]:
        """Get entries matching any of the provided tags."""
        matching = []
        for entry in self.entries.values():
            if any(tag in entry.tags for tag in tags):
                matching.append(entry)
        return matching
    
    def mark_verified(self, entry_id: str) -> None:
        """Mark an entry as human-verified."""
        if entry_id in self.entries:
            self.entries[entry_id].human_verified = True
            self.entries[entry_id].last_updated = datetime.utcnow().isoformat()
            logger.info(f"Marked entry as verified: {entry_id}")
    
    def get_verified_entries(self) -> List[MemoryEntry]:
        """Get only human-verified entries."""
        return [e for e in self.entries.values() if e.human_verified]
    
    def get_high_confidence(self, threshold: float = 0.8) -> List[MemoryEntry]:
        """Get entries above confidence threshold."""
        return [
            e for e in self.entries.values()
            if e.confidence >= threshold
        ]
    
    def merge_entry(self, new_entry: MemoryEntry) -> None:
        """
        Merge a new entry with an existing one, or add it if new.
        Increases confidence if pattern is seen again.
        """
        # Check if similar entry exists (by title and category)
        existing = None
        for entry in self.entries.values():
            if (entry.title.lower() == new_entry.title.lower() and
                entry.category == new_entry.category):
                existing = entry
                break
        
        if existing:
            # Increase confidence (capped at 1.0)
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.last_updated = datetime.utcnow().isoformat()
            
            # Merge examples and sources
            existing.examples.extend(new_entry.examples)
            existing.source_files.extend(new_entry.source_files)
            
            # Keep unique
            existing.examples = list(set(existing.examples))
            existing.source_files = list(set(existing.source_files))
            existing.tags = list(set(existing.tags + new_entry.tags))
            
            logger.info(f"Merged entry: {existing.title} (confidence: {existing.confidence:.1f})")
        else:
            self.add_entry(new_entry)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of project memory."""
        entries_by_category = {}
        for category in MemoryCategory:
            entries_by_category[category.value] = len(self.get_by_category(category))
        
        return {
            "repo_root": self.repo_root,
            "total_entries": len(self.entries),
            "verified_entries": len(self.get_verified_entries()),
            "avg_confidence": sum(e.confidence for e in self.entries.values()) / max(1, len(self.entries)),
            "entries_by_category": entries_by_category,
            "learned_conventions": len(self.learned_conventions),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "repo_root": self.repo_root,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "learned_conventions": list(self.learned_conventions),
            "summary": self.get_summary(),
        }

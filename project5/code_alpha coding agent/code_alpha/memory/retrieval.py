"""
Memory retrieval and semantic matching for context injection.

Retrieves relevant conventions based on task context.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from difflib import SequenceMatcher

from .core import ProjectMemory, MemoryEntry, MemoryCategory

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    """Context about which memories to use for a task."""
    
    task_description: str
    relevant_entries: List[MemoryEntry]
    high_confidence_entries: List[MemoryEntry]
    human_verified_entries: List[MemoryEntry]
    formatted_context: str


class SemanticMatcher:
    """
    Semantic similarity matching for memory retrieval.
    
    Uses simple string similarity for pattern matching.
    Can be enhanced with embeddings in future versions.
    """
    
    @staticmethod
    def similarity(text1: str, text2: str) -> float:
        """
        Calculate string similarity score (0.0-1.0).
        
        Uses SequenceMatcher for simple similarity.
        In production, would use embeddings (OpenAI, Hugging Face, etc.)
        """
        # Normalize
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Quick win: exact or substring match
        if t1 in t2 or t2 in t1:
            return 0.95
        
        # Use SequenceMatcher for fuzzy matching
        matcher = SequenceMatcher(None, t1, t2)
        ratio = matcher.ratio()
        
        return ratio
    
    @staticmethod
    def match_tags(task_tags: List[str], entry_tags: List[str]) -> float:
        """Calculate tag-based similarity."""
        if not task_tags or not entry_tags:
            return 0.0
        
        matches = len(set(task_tags) & set(entry_tags))
        total = len(set(task_tags) | set(entry_tags))
        
        return matches / total if total > 0 else 0.0


class MemoryRetriever:
    """
    Retrieves relevant memories for a given task.
    
    Strategies:
    1. Human-verified entries (highest priority)
    2. High-confidence entries (> 0.8)
    3. Semantic match to task description
    4. Category-based suggestions
    """
    
    def __init__(self, memory: ProjectMemory):
        self.memory = memory
        self.matcher = SemanticMatcher()
    
    def retrieve_for_task(
        self,
        task_description: str,
        task_category: Optional[MemoryCategory] = None,
        task_tags: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> MemoryContext:
        """
        Retrieve memories relevant to a task.
        
        Args:
            task_description: Description of the task
            task_category: Optional category hint
            task_tags: Optional tags for the task
            top_k: Number of top results to return
        
        Returns:
            MemoryContext with relevant entries and formatted context
        """
        candidates = []
        
        # 1. Human-verified entries (highest priority)
        verified = self.memory.get_verified_entries()
        for entry in verified:
            score = self._score_entry(entry, task_description, task_category, task_tags)
            candidates.append((entry, score, "verified"))
        
        # 2. High-confidence entries
        high_conf = self.memory.get_high_confidence(threshold=0.8)
        for entry in high_conf:
            if entry not in verified:  # Avoid duplicates
                score = self._score_entry(entry, task_description, task_category, task_tags)
                candidates.append((entry, score, "high_confidence"))
        
        # 3. All entries with semantic matching
        for entry in self.memory.entries.values():
            if entry not in verified and entry not in high_conf:
                score = self._score_entry(entry, task_description, task_category, task_tags)
                if score > 0.3:  # Filter weak matches
                    candidates.append((entry, score, "semantic"))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Extract top entries
        top_entries = [entry for entry, score, _ in candidates[:top_k]]
        high_conf_entries = [entry for entry, score, priority in candidates if priority in ["verified", "high_confidence"]][:top_k]
        verified_entries = [entry for entry, score, priority in candidates if priority == "verified"][:top_k]
        
        # Format context
        formatted = self._format_context(top_entries, task_description)
        
        return MemoryContext(
            task_description=task_description,
            relevant_entries=top_entries,
            high_confidence_entries=high_conf_entries,
            human_verified_entries=verified_entries,
            formatted_context=formatted,
        )
    
    def _score_entry(
        self,
        entry: MemoryEntry,
        task_description: str,
        task_category: Optional[MemoryCategory],
        task_tags: Optional[List[str]],
    ) -> float:
        """
        Score an entry for relevance to a task.
        
        Combines multiple signals:
        - Semantic similarity (0.4 weight)
        - Category match (0.3 weight)
        - Tag match (0.2 weight)
        - Confidence (0.1 weight)
        """
        score = 0.0
        
        # 1. Semantic similarity to description and title
        desc_sim = self.matcher.similarity(task_description, entry.description)
        title_sim = self.matcher.similarity(task_description, entry.title)
        semantic_score = max(desc_sim, title_sim)
        score += semantic_score * 0.4
        
        # 2. Category match
        if task_category and entry.category == task_category:
            score += 0.3
        elif task_category is None:
            # Slight boost if no category specified (broader match)
            score += 0.1
        
        # 3. Tag match
        if task_tags:
            tag_score = self.matcher.match_tags(task_tags, entry.tags)
            score += tag_score * 0.2
        
        # 4. Confidence
        score += entry.confidence * 0.1
        
        return score
    
    def _format_context(self, entries: List[MemoryEntry], task_description: str) -> str:
        """
        Format memory entries as context for agent.
        
        Returns readable text suitable for injection into prompts.
        """
        if not entries:
            return ""
        
        lines = [
            "# Project Conventions & Learned Patterns",
            "",
            f"Based on task: {task_description}",
            "",
        ]
        
        by_category: Dict[MemoryCategory, List[MemoryEntry]] = {}
        for entry in entries:
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry)
        
        for category, cat_entries in by_category.items():
            lines.append(f"## {category.value.replace('_', ' ').title()}")
            lines.append("")
            
            for entry in cat_entries:
                # Title and confidence
                verified_marker = " ✓ (human verified)" if entry.human_verified else ""
                lines.append(f"### {entry.title}{verified_marker}")
                lines.append(f"*Confidence: {entry.confidence:.0%}*")
                lines.append("")
                
                # Description
                lines.append(entry.description)
                lines.append("")
                
                # Examples if available
                if entry.examples:
                    lines.append("**Examples:**")
                    for example in entry.examples[:3]:  # Limit to 3 examples
                        lines.append(f"- `{example}`")
                    lines.append("")
                
                # Rationale if available
                if entry.rationale:
                    lines.append(f"**Rationale:** {entry.rationale}")
                    lines.append("")
        
        return "\n".join(lines)
    
    def get_memory_for_context(
        self,
        task_description: str,
        limit: int = 3,
    ) -> str:
        """
        Get formatted memory context for injection into prompts.
        
        Simple interface for agent integration.
        """
        context = self.retrieve_for_task(task_description, top_k=limit)
        return context.formatted_context
    
    def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """
        Search memory by free-text query.
        
        Returns top matching entries.
        """
        scored = []
        
        for entry in self.memory.entries.values():
            # Score against title, description, and examples
            title_score = self.matcher.similarity(query, entry.title)
            desc_score = self.matcher.similarity(query, entry.description)
            examples_score = max(
                (self.matcher.similarity(query, ex) for ex in entry.examples),
                default=0.0
            )
            
            score = max(title_score, desc_score, examples_score)
            
            if score > 0.2:  # Filter weak matches
                scored.append((entry, score))
        
        # Sort and return top
        scored.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in scored[:top_k]]

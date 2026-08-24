"""
Memory storage adapter for persistent project conventions.

Handles serialization/deserialization to .codealpha/memory.json
Maintains human-readable, version-controlled memory files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .core import ProjectMemory, MemoryEntry, MemoryCategory

logger = logging.getLogger(__name__)


class MemoryAdapter:
    """
    Adapter for persisting project memory to disk.
    
    Storage format:
    - .codealpha/memory.json: Machine-readable JSON
    - .codealpha/memory.md: Human-readable markdown (optional)
    
    The JSON file is the source of truth, markdown is for reference.
    """
    
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.codealpha_dir = self.repo_root / ".codealpha"
        self.memory_file = self.codealpha_dir / "memory.json"
        self.memory_md = self.codealpha_dir / "memory.md"
        
        # Ensure directory exists
        self.codealpha_dir.mkdir(exist_ok=True)
    
    def load(self) -> ProjectMemory:
        """
        Load project memory from disk.
        
        Creates new ProjectMemory if file doesn't exist.
        """
        memory = ProjectMemory(repo_root=str(self.repo_root))
        
        if not self.memory_file.exists():
            logger.info(f"No memory file found at {self.memory_file}, creating new")
            return memory
        
        try:
            with open(self.memory_file, 'r') as f:
                data = json.load(f)
            
            # Restore entries
            for entry_id, entry_data in data.get('entries', {}).items():
                entry = self._deserialize_entry(entry_data)
                memory.entries[entry_id] = entry
            
            # Restore learned conventions
            memory.learned_conventions = set(data.get('learned_conventions', []))
            
            logger.info(f"Loaded {len(memory.entries)} memory entries from {self.memory_file}")
            
        except Exception as e:
            logger.error(f"Error loading memory file: {e}")
            raise
        
        return memory
    
    def save(self, memory: ProjectMemory) -> None:
        """
        Save project memory to disk.
        
        Updates both JSON (machine-readable) and MD (human-readable).
        """
        # Ensure directory exists
        self.codealpha_dir.mkdir(exist_ok=True)
        
        # Prepare data
        data = {
            "repo_root": str(memory.repo_root),
            "entries": {
                entry_id: entry.to_dict()
                for entry_id, entry in memory.entries.items()
            },
            "learned_conventions": list(memory.learned_conventions),
            "summary": memory.get_summary(),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        # Save JSON
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved memory to {self.memory_file}")
        except Exception as e:
            logger.error(f"Error saving memory file: {e}")
            raise
        
        # Generate and save markdown for human reference
        try:
            md_content = self._generate_markdown(memory, data)
            with open(self.memory_md, 'w') as f:
                f.write(md_content)
            logger.info(f"Generated memory markdown at {self.memory_md}")
        except Exception as e:
            logger.debug(f"Error generating markdown: {e}")
    
    def _deserialize_entry(self, data: Dict[str, Any]) -> MemoryEntry:
        """Deserialize MemoryEntry from JSON data."""
        return MemoryEntry(
            id=data['id'],
            category=MemoryCategory(data['category']),
            title=data['title'],
            description=data['description'],
            examples=data.get('examples', []),
            rationale=data.get('rationale', ''),
            confidence=data.get('confidence', 1.0),
            first_seen=data.get('first_seen', datetime.utcnow().isoformat()),
            last_updated=data.get('last_updated', datetime.utcnow().isoformat()),
            human_verified=data.get('human_verified', False),
            tags=data.get('tags', []),
            related_entries=data.get('related_entries', []),
            source_files=data.get('source_files', []),
        )
    
    def _generate_markdown(self, memory: ProjectMemory, data: Dict[str, Any]) -> str:
        """
        Generate human-readable markdown from memory.
        
        Format:
        # Project Memory & Conventions
        
        Generated from .codealpha/memory.json
        Last updated: [date]
        
        ## Statistics
        - Total entries: N
        - Verified entries: N
        - Categories: [list]
        
        ## Conventions by Category
        ### Category Name
        - Convention 1 (confidence: 95%)
        - Convention 2 (confidence: 85%)
        ...
        """
        lines = [
            "# Project Memory & Conventions",
            "",
            f"Repository: {memory.repo_root}",
            f"Last updated: {data['last_updated']}",
            "",
            "## ℹ️ About This File",
            "",
            "This file documents learned conventions and architectural decisions for this project.",
            "It is auto-generated from `.codealpha/memory.json` but kept human-readable.",
            "",
            "**How to use:**",
            "- Review conventions to understand project patterns",
            "- Edit `.codealpha/memory.json` directly to modify entries",
            "- Mark entries as verified by setting `human_verified: true`",
            "- Keep this file version-controlled with your repo",
            "",
            "---",
            "",
        ]
        
        # Statistics
        summary = data['summary']
        lines.extend([
            "## 📊 Statistics",
            "",
            f"- **Total entries:** {summary['total_entries']}",
            f"- **Verified entries:** {summary['verified_entries']}",
            f"- **Average confidence:** {summary['avg_confidence']:.0%}",
            f"- **Learned conventions:** {summary['learned_conventions']}",
            "",
            "### Entries by Category",
            "",
        ])
        
        for category, count in summary['entries_by_category'].items():
            if count > 0:
                lines.append(f"- {category.replace('_', ' ').title()}: {count}")
        
        lines.extend(["", "---", ""])
        
        # Entries by category
        entries_by_cat: Dict[MemoryCategory, List[MemoryEntry]] = {}
        for entry in memory.entries.values():
            if entry.category not in entries_by_cat:
                entries_by_cat[entry.category] = []
            entries_by_cat[entry.category].append(entry)
        
        for category in MemoryCategory:
            if category not in entries_by_cat:
                continue
            
            lines.append(f"## {category.value.replace('_', ' ').title()}")
            lines.append("")
            
            for entry in entries_by_cat[category]:
                # Entry header
                verified_badge = " ✓" if entry.human_verified else ""
                lines.append(f"### {entry.title}{verified_badge}")
                lines.append(f"**Confidence:** {entry.confidence:.0%}")
                
                if entry.tags:
                    lines.append(f"**Tags:** {', '.join(f'`{tag}`' for tag in entry.tags)}")
                
                lines.append("")
                lines.append(entry.description)
                lines.append("")
                
                if entry.rationale:
                    lines.append(f"**Rationale:** {entry.rationale}")
                    lines.append("")
                
                if entry.examples:
                    lines.append("**Examples:**")
                    lines.append("")
                    for example in entry.examples[:5]:
                        lines.append(f"```")
                        lines.append(example)
                        lines.append("```")
                        lines.append("")
                
                if entry.source_files:
                    files_str = ", ".join(f"`{Path(f).name}`" for f in entry.source_files[:3])
                    lines.append(f"**Found in:** {files_str}")
                    lines.append("")
                
                lines.append("---")
                lines.append("")
        
        lines.extend([
            "## 📝 How to Edit",
            "",
            "To modify memory entries:",
            "1. Edit `.codealpha/memory.json` directly",
            "2. Set `human_verified: true` for verified conventions",
            "3. Commit both `.codealpha/memory.json` and this file to version control",
            "",
            "The agent will respect human-verified entries over inferred ones.",
            "",
        ])
        
        return "\n".join(lines)


class MemoryManager:
    """
    High-level memory management interface.
    
    Combines loading, extraction, retrieval, and storage.
    """
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.adapter = MemoryAdapter(repo_root)
        self.memory = self.adapter.load()
    
    def refresh(self) -> None:
        """Reload memory from disk."""
        self.memory = self.adapter.load()
    
    def save(self) -> None:
        """Persist memory to disk."""
        self.adapter.save(self.memory)
    
    def get_memory(self) -> ProjectMemory:
        """Get current memory instance."""
        return self.memory
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto-save on exit."""
        if exc_type is None:  # Only save if no exception
            self.save()

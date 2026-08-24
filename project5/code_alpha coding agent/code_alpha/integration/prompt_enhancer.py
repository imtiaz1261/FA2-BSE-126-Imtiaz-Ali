"""
Prompt enhancer for injecting learned conventions into LLM prompts.

Automatically enhances prompts with relevant project patterns and conventions.
"""

import logging
from typing import List, Optional
from jinja2 import Template

from code_alpha.memory import MemoryRetriever, ProjectMemory, MemoryEntry

logger = logging.getLogger(__name__)


class PromptEnhancer:
    """
    Enhances LLM prompts with learned project conventions.
    
    Strategies:
    1. Semantic matching of task description to learned conventions
    2. Category-based convention injection
    3. Human-verified entry prioritization
    """
    
    def __init__(self, memory: ProjectMemory):
        self.memory = memory
        self.retriever = MemoryRetriever(memory)
        
        # Prompt templates
        self.convention_template = Template("""
## Project Conventions & Patterns

Based on learned patterns in this project, follow these conventions:

{% for entry in entries %}
### {{ entry.title }}
{{ entry.description }}
{% if entry.examples %}
Examples:
{% for example in entry.examples[:3] %}
- `{{ example }}`
{% endfor %}
{% endif %}

{% endfor %}
""")
        
        self.style_template = Template("""
## Code Style Guide

This project follows these code style conventions:

{% for entry in style_entries %}
- {{ entry.description }}
{% endfor %}
""")
    
    def enhance_prompt(
        self,
        base_prompt: str,
        task_description: Optional[str] = None,
        include_verified_only: bool = False,
        max_conventions: int = 5,
    ) -> str:
        """
        Enhance prompt with conventions.
        
        Args:
            base_prompt: Original prompt
            task_description: Optional task description for semantic matching
            include_verified_only: Only include human-verified entries
            max_conventions: Maximum conventions to include
        
        Returns:
            Enhanced prompt with conventions
        """
        # Get relevant conventions
        if task_description:
            context = self.retriever.retrieve_for_task(
                task_description,
                top_k=max_conventions,
            )
            if include_verified_only:
                entries = context.human_verified_entries[:max_conventions]
            else:
                entries = context.relevant_entries[:max_conventions]
        else:
            entries = self.memory.get_high_confidence(threshold=0.8)[:max_conventions]
        
        if not entries:
            return base_prompt
        
        # Render convention section
        conventions_text = self.convention_template.render(entries=entries)
        
        # Combine with original prompt
        enhanced = f"{base_prompt}\n\n{conventions_text}"
        
        logger.debug(f"Enhanced prompt with {len(entries)} conventions")
        
        return enhanced
    
    def enhance_with_style_guide(
        self,
        base_prompt: str,
        max_styles: int = 5,
    ) -> str:
        """
        Enhance prompt with project code style conventions.
        
        Args:
            base_prompt: Original prompt
            max_styles: Maximum style conventions to include
        
        Returns:
            Enhanced prompt with style guide
        """
        from code_alpha.memory import MemoryCategory
        
        # Get style-related conventions
        style_entries = self.memory.get_by_category(MemoryCategory.CODE_STYLE)[:max_styles]
        
        if not style_entries:
            return base_prompt
        
        # Render style section
        style_text = self.style_template.render(style_entries=style_entries)
        
        # Combine
        enhanced = f"{base_prompt}\n\n{style_text}"
        
        return enhanced
    
    def enhance_with_error_handling(self, base_prompt: str) -> str:
        """
        Enhance prompt with error handling patterns.
        
        Args:
            base_prompt: Original prompt
        
        Returns:
            Enhanced prompt
        """
        from code_alpha.memory import MemoryCategory
        
        entries = self.memory.get_by_category(MemoryCategory.ERROR_HANDLING)[:3]
        
        if not entries:
            return base_prompt
        
        text = "\n## Error Handling\n\n"
        for entry in entries:
            text += f"- {entry.description}\n"
            if entry.examples:
                text += f"  Example: `{entry.examples[0]}`\n"
        
        return f"{base_prompt}\n{text}"
    
    def enhance_with_testing(self, base_prompt: str) -> str:
        """
        Enhance prompt with testing conventions.
        
        Args:
            base_prompt: Original prompt
        
        Returns:
            Enhanced prompt
        """
        from code_alpha.memory import MemoryCategory
        
        entries = self.memory.get_by_category(MemoryCategory.TESTING)[:3]
        
        if not entries:
            return base_prompt
        
        text = "\n## Testing Conventions\n\n"
        for entry in entries:
            text += f"- {entry.description}\n"
        
        return f"{base_prompt}\n{text}"
    
    def enhance_for_phase(
        self,
        base_prompt: str,
        phase: str,
        task_description: Optional[str] = None,
    ) -> str:
        """
        Enhance prompt based on execution phase.
        
        Args:
            base_prompt: Original prompt
            phase: Current phase (planning, generating, testing, fixing)
            task_description: Optional task description
        
        Returns:
            Phase-specific enhanced prompt
        """
        enhanced = base_prompt
        
        # Add phase-specific conventions
        if phase == "planning":
            from code_alpha.memory import MemoryCategory
            entries = self.memory.get_by_category(MemoryCategory.ARCHITECTURE)[:3]
            if entries:
                enhanced += "\n## Architecture Patterns\n"
                for entry in entries:
                    enhanced += f"- {entry.description}\n"
        
        elif phase == "implementing":
            enhanced = self.enhance_with_style_guide(enhanced)
            enhanced = self.enhance_with_error_handling(enhanced)
        
        elif phase == "testing":
            enhanced = self.enhance_with_testing(enhanced)
        
        elif phase == "fixing":
            enhanced = self.enhance_with_error_handling(enhanced)
        
        # Add semantic matches if task description provided
        if task_description:
            enhanced = self.enhance_prompt(enhanced, task_description, max_conventions=3)
        
        return enhanced
    
    def get_context_string(self) -> str:
        """
        Get full context string of all learned conventions.
        
        Useful for summarizing what the system has learned.
        """
        verified = self.memory.get_verified_entries()
        
        if not verified:
            return "No verified conventions yet."
        
        lines = ["## Learned Project Conventions", ""]
        
        by_category = {}
        for entry in verified:
            cat = entry.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(entry)
        
        for category, entries in by_category.items():
            lines.append(f"### {category.value.replace('_', ' ').title()}")
            for entry in entries:
                lines.append(f"- {entry.title}")
            lines.append("")
        
        return "\n".join(lines)

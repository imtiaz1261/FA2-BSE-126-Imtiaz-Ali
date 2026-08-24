"""
Convention extraction from completed tasks.

Analyzes task execution results to identify durable project conventions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import re
import logging
import uuid

from .core import ProjectMemory, MemoryEntry, MemoryCategory

logger = logging.getLogger(__name__)


@dataclass
class ConventionPattern:
    """A detected convention pattern with supporting evidence."""
    
    category: MemoryCategory
    title: str
    description: str
    confidence: float
    examples: List[str]
    source_files: List[str]
    tags: List[str]


class ConventionExtractor:
    """
    Extracts conventions from analyzed codebase.
    
    Looks for patterns in:
    - Naming conventions (functions, variables, classes)
    - Code organization and structure
    - Error handling approaches
    - Library usage
    - API design patterns
    - Testing patterns
    """
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.repo_path = Path(repo_root)
    
    def extract_naming_conventions(self) -> List[ConventionPattern]:
        """Extract naming conventions from codebase."""
        patterns = []
        
        # Scan Python files for naming patterns
        py_files = list(self.repo_path.rglob("*.py"))[:20]  # Sample first 20 files
        
        function_names = []
        class_names = []
        constant_names = []
        
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                
                # Extract function names
                func_pattern = r'def\s+([a-z_][a-z0-9_]*)\s*\('
                function_names.extend(re.findall(func_pattern, content))
                
                # Extract class names
                class_pattern = r'class\s+([A-Z][a-zA-Z0-9]*)\s*[:\(]'
                class_names.extend(re.findall(class_pattern, content))
                
                # Extract constants (ALL_CAPS)
                const_pattern = r'([A-Z][A-Z0-9_]*)\s*='
                constant_names.extend(re.findall(const_pattern, content))
                
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
        
        # Detect snake_case vs camelCase
        if function_names:
            snake_count = sum(1 for n in function_names if '_' in n)
            camel_count = sum(1 for n in function_names if any(c.isupper() for c in n))
            
            naming_style = "snake_case" if snake_count > camel_count else "camelCase"
            
            patterns.append(ConventionPattern(
                category=MemoryCategory.NAMING,
                title=f"Function naming: {naming_style}",
                description=f"Functions use {naming_style} naming convention",
                confidence=min(0.95, max(0.7, snake_count / max(1, len(function_names)))),
                examples=function_names[:5],
                source_files=[str(f) for f in py_files[:3]],
                tags=["naming", "functions", naming_style],
            ))
        
        if class_names:
            patterns.append(ConventionPattern(
                category=MemoryCategory.NAMING,
                title="Class naming: PascalCase",
                description="Classes use PascalCase naming convention",
                confidence=0.95,
                examples=class_names[:5],
                source_files=[str(f) for f in py_files[:3]],
                tags=["naming", "classes", "PascalCase"],
            ))
        
        return patterns
    
    def extract_library_preferences(self) -> List[ConventionPattern]:
        """Extract library and framework preferences."""
        patterns = []
        
        try:
            # Check requirements files
            req_files = [
                self.repo_path / "requirements.txt",
                self.repo_path / "requirements_cli_api.txt",
                self.repo_path / "pyproject.toml",
            ]
            
            libraries = {}
            for req_file in req_files:
                if req_file.exists():
                    content = req_file.read_text()
                    # Extract library names
                    for line in content.split('\n'):
                        if '==' in line:
                            lib = line.split('==')[0].strip()
                            libraries[lib] = libraries.get(lib, 0) + 1
            
            # Detect framework preferences
            framework_keywords = {
                'fastapi': ('FastAPI', 'Web Framework'),
                'typer': ('Typer', 'CLI Framework'),
                'pydantic': ('Pydantic', 'Data Validation'),
                'pytest': ('Pytest', 'Testing Framework'),
            }
            
            for lib, (name, desc) in framework_keywords.items():
                if lib in libraries:
                    patterns.append(ConventionPattern(
                        category=MemoryCategory.LIBRARIES,
                        title=f"Uses {name}",
                        description=f"Project uses {name} for {desc}",
                        confidence=0.95,
                        examples=[lib],
                        source_files=[str(f) for f in req_files if f.exists()],
                        tags=["libraries", "framework", lib],
                    ))
        
        except Exception as e:
            logger.debug(f"Error extracting library preferences: {e}")
        
        return patterns
    
    def extract_error_handling(self) -> List[ConventionPattern]:
        """Detect error handling patterns."""
        patterns = []
        
        try:
            py_files = list(self.repo_path.rglob("*.py"))[:15]
            
            try_except_count = 0
            result_pattern_count = 0
            custom_exception_count = 0
            
            for py_file in py_files:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                try_except_count += len(re.findall(r'try:', content))
                result_pattern_count += len(re.findall(r'Result\[', content))
                custom_exception_count += len(re.findall(r'class.*Exception\)', content))
            
            if try_except_count > result_pattern_count:
                patterns.append(ConventionPattern(
                    category=MemoryCategory.ERROR_HANDLING,
                    title="Try/except error handling",
                    description="Project uses try/except blocks for error handling",
                    confidence=0.85,
                    examples=["try: ... except Exception as e: ..."],
                    source_files=[str(f) for f in py_files[:3]],
                    tags=["error_handling", "exceptions"],
                ))
            
            if custom_exception_count > 0:
                patterns.append(ConventionPattern(
                    category=MemoryCategory.ERROR_HANDLING,
                    title="Custom exception classes",
                    description="Project defines custom exception classes",
                    confidence=0.90,
                    examples=["Custom exception classes for domain-specific errors"],
                    source_files=[str(f) for f in py_files[:3]],
                    tags=["error_handling", "exceptions", "custom"],
                ))
        
        except Exception as e:
            logger.debug(f"Error extracting error handling patterns: {e}")
        
        return patterns
    
    def extract_api_patterns(self) -> List[ConventionPattern]:
        """Extract API design patterns."""
        patterns = []
        
        try:
            # Look for FastAPI patterns
            api_files = list(self.repo_path.rglob("**/api/**/*.py"))
            
            if api_files:
                content = "\n".join(
                    f.read_text(encoding='utf-8', errors='ignore')
                    for f in api_files[:5]
                )
                
                # Check for RESTful patterns
                if '@app.get' in content or '@app.post' in content:
                    patterns.append(ConventionPattern(
                        category=MemoryCategory.API,
                        title="RESTful API design",
                        description="Project uses RESTful API patterns with FastAPI",
                        confidence=0.95,
                        examples=["@app.get('/endpoint')", "@app.post('/endpoint')"],
                        source_files=[str(f) for f in api_files[:3]],
                        tags=["api", "rest", "fastapi"],
                    ))
                
                # Check for pagination
                if 'limit' in content and 'offset' in content:
                    patterns.append(ConventionPattern(
                        category=MemoryCategory.API,
                        title="Limit/offset pagination",
                        description="API uses limit/offset pagination pattern",
                        confidence=0.85,
                        examples=["limit: int", "offset: int"],
                        source_files=[str(f) for f in api_files[:2]],
                        tags=["api", "pagination"],
                    ))
        
        except Exception as e:
            logger.debug(f"Error extracting API patterns: {e}")
        
        return patterns
    
    def extract_all_conventions(self) -> List[ConventionPattern]:
        """Extract all detectable conventions."""
        patterns = []
        
        logger.info(f"Extracting conventions from {self.repo_root}...")
        
        patterns.extend(self.extract_naming_conventions())
        patterns.extend(self.extract_library_preferences())
        patterns.extend(self.extract_error_handling())
        patterns.extend(self.extract_api_patterns())
        
        logger.info(f"Extracted {len(patterns)} convention patterns")
        
        return patterns


class MemoryExtractor:
    """
    Orchestrates convention extraction and memory update.
    
    Runs after task completion to identify patterns worth remembering.
    """
    
    def __init__(self, memory: ProjectMemory):
        self.memory = memory
        self.convention_extractor = ConventionExtractor(memory.repo_root)
    
    def extract_and_update(self) -> int:
        """
        Extract conventions and update project memory.
        
        Returns:
            Number of new/updated entries added
        """
        patterns = self.convention_extractor.extract_all_conventions()
        updated_count = 0
        
        for pattern in patterns:
            # Create memory entry from pattern
            entry = MemoryEntry(
                id=f"mem_{uuid.uuid4().hex[:8]}",
                category=pattern.category,
                title=pattern.title,
                description=pattern.description,
                examples=pattern.examples,
                confidence=pattern.confidence,
                tags=pattern.tags,
                source_files=pattern.source_files,
            )
            
            # Merge with existing (increases confidence if seen again)
            self.memory.merge_entry(entry)
            updated_count += 1
        
        logger.info(f"Updated memory with {updated_count} conventions")
        return updated_count
    
    def extract_from_task_result(self, task_result: Dict[str, Any]) -> int:
        """
        Extract conventions from completed task result.
        
        Args:
            task_result: Result dictionary from task execution
        
        Returns:
            Number of entries added/updated
        """
        # Enhanced extraction can look at task-specific results
        # For now, rely on general codebase analysis
        return self.extract_and_update()

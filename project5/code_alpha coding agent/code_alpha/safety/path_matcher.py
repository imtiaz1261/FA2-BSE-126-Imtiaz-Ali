"""
Sensitive Path Matcher for Code Alpha Safety

Matches file paths against glob patterns with high performance.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from pathlib import Path
from fnmatch import fnmatch
import os
import logging

logger = logging.getLogger(__name__)


class MatchType(str, Enum):
    """Types of path matches."""
    EXACT = "exact"
    GLOB = "glob"
    PARENT_DIR = "parent_dir"
    EXTENSION = "extension"
    NONE = "none"


@dataclass
class MatchResult:
    """Result of path matching."""
    
    path: str
    matched: bool
    match_type: Optional[MatchType] = None
    pattern: Optional[str] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'path': self.path,
            'matched': self.matched,
            'match_type': self.match_type.value if self.match_type else None,
            'pattern': self.pattern,
            'reason': self.reason,
        }


class PathMatcher:
    """
    Matches file paths against sensitive patterns.
    
    Supports glob patterns, exact matches, and parent directory matching.
    Optimized for performance with caching.
    """
    
    # Commonly blocked extensions
    DEFAULT_BLOCKED_EXTENSIONS = {
        '.env', '.pem', '.key', '.crt', '.pfx',
        '.p12', '.jks', '.keystore', '.credentials',
    }
    
    # Default sensitive directories
    DEFAULT_SENSITIVE_DIRS = {
        '.env', '.secrets', '.credentials', 'secrets',
        'config/prod', 'config/production', 'infra',
        'terraform', 'ansible', '.github', '.gitlab-ci.yml',
    }
    
    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        blocked_extensions: Optional[Set[str]] = None,
        case_sensitive: bool = False,
    ):
        """
        Initialize path matcher.
        
        Args:
            patterns: Glob patterns for sensitive paths
            blocked_extensions: File extensions to block
            case_sensitive: Whether matching is case-sensitive
        """
        self.patterns = patterns or []
        self.blocked_extensions = blocked_extensions or self.DEFAULT_BLOCKED_EXTENSIONS
        self.case_sensitive = case_sensitive
        
        # Cache for compiled patterns
        self._pattern_cache: Dict[str, bool] = {}
        self._max_cache_size = 10000
        
        logger.info(
            f"PathMatcher initialized with {len(self.patterns)} patterns, "
            f"{len(self.blocked_extensions)} blocked extensions"
        )
    
    def matches(self, path: str) -> MatchResult:
        """
        Check if path matches any sensitive pattern.
        
        Returns MatchResult with detailed information.
        """
        # Normalize path
        normalized = self._normalize_path(path)
        
        # Check cache
        if normalized in self._pattern_cache:
            if self._pattern_cache[normalized]:
                return MatchResult(
                    path=path,
                    matched=True,
                    match_type=MatchType.GLOB,
                    reason="Cached match",
                )
            else:
                return MatchResult(
                    path=path,
                    matched=False,
                )
        
        # Check blocked extensions
        ext_result = self._check_extension(normalized)
        if ext_result.matched:
            self._cache_result(normalized, True)
            return ext_result
        
        # Check glob patterns
        pattern_result = self._check_patterns(normalized)
        if pattern_result.matched:
            self._cache_result(normalized, True)
            return pattern_result
        
        # Check parent directories
        parent_result = self._check_parent_dirs(normalized)
        if parent_result.matched:
            self._cache_result(normalized, True)
            return parent_result
        
        # No match
        self._cache_result(normalized, False)
        return MatchResult(
            path=path,
            matched=False,
            match_type=MatchType.NONE,
        )
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for consistent matching."""
        # Convert to forward slashes
        path = path.replace('\\', '/')
        
        # Remove leading ./
        if path.startswith('./'):
            path = path[2:]
        
        # Normalize case if case-insensitive
        if not self.case_sensitive:
            path = path.lower()
        
        return path
    
    def _check_extension(self, path: str) -> MatchResult:
        """Check if file extension is blocked."""
        _, ext = os.path.splitext(path)
        
        check_ext = ext if self.case_sensitive else ext.lower()
        
        if check_ext in self.blocked_extensions:
            return MatchResult(
                path=path,
                matched=True,
                match_type=MatchType.EXTENSION,
                pattern=f"*.{check_ext}",
                reason=f"File extension '{check_ext}' is blocked",
            )
        
        return MatchResult(path=path, matched=False)
    
    def _check_patterns(self, path: str) -> MatchResult:
        """Check against configured glob patterns."""
        for pattern in self.patterns:
            # For case-insensitive, convert both to same case for fnmatch
            if self.case_sensitive:
                pattern_check = pattern
                path_check = path
            else:
                pattern_check = pattern.lower()
                path_check = path.lower()
            
            if fnmatch(path_check, pattern_check) or fnmatch(path_check, f"*{pattern_check}*"):
                return MatchResult(
                    path=path,
                    matched=True,
                    match_type=MatchType.GLOB,
                    pattern=pattern,
                    reason=f"Path matches sensitive pattern '{pattern}'",
                )
        
        return MatchResult(path=path, matched=False)
    
    def _check_parent_dirs(self, path: str) -> MatchResult:
        """Check if parent directory is sensitive."""
        parts = path.split('/')
        
        for part in parts:
            check_part = part if self.case_sensitive else part.lower()
            
            if check_part in self.DEFAULT_SENSITIVE_DIRS:
                return MatchResult(
                    path=path,
                    matched=True,
                    match_type=MatchType.PARENT_DIR,
                    pattern=check_part,
                    reason=f"Path is under sensitive directory '{check_part}'",
                )
        
        return MatchResult(path=path, matched=False)
    
    def _cache_result(self, path: str, matched: bool) -> None:
        """Cache match result."""
        # Implement simple LRU eviction if cache gets too large
        if len(self._pattern_cache) >= self._max_cache_size:
            # Remove oldest 10% of entries
            to_remove = len(self._pattern_cache) // 10
            for key in list(self._pattern_cache.keys())[:to_remove]:
                del self._pattern_cache[key]
        
        self._pattern_cache[path] = matched
    
    def add_pattern(self, pattern: str) -> None:
        """Add a sensitive path pattern."""
        if pattern not in self.patterns:
            self.patterns.append(pattern)
            self._pattern_cache.clear()  # Invalidate cache
            logger.info(f"Added sensitive pattern: {pattern}")
    
    def remove_pattern(self, pattern: str) -> None:
        """Remove a sensitive path pattern."""
        if pattern in self.patterns:
            self.patterns.remove(pattern)
            self._pattern_cache.clear()  # Invalidate cache
            logger.info(f"Removed sensitive pattern: {pattern}")
    
    def add_blocked_extension(self, extension: str) -> None:
        """Add a blocked file extension."""
        # Ensure extension starts with .
        if not extension.startswith('.'):
            extension = f".{extension}"
        
        if extension not in self.blocked_extensions:
            self.blocked_extensions.add(extension)
            self._pattern_cache.clear()  # Invalidate cache
            logger.info(f"Added blocked extension: {extension}")
    
    def get_statistics(self) -> Dict:
        """Get matcher statistics."""
        return {
            'total_patterns': len(self.patterns),
            'total_blocked_extensions': len(self.blocked_extensions),
            'cache_size': len(self._pattern_cache),
            'max_cache_size': self._max_cache_size,
            'case_sensitive': self.case_sensitive,
        }
    
    def clear_cache(self) -> None:
        """Clear the pattern cache."""
        old_size = len(self._pattern_cache)
        self._pattern_cache.clear()
        logger.info(f"Cleared cache ({old_size} entries)")
    
    def batch_check(self, paths: List[str]) -> List[MatchResult]:
        """
        Check multiple paths efficiently.
        
        More efficient than calling matches() repeatedly.
        """
        return [self.matches(path) for path in paths]
    
    def find_matches(self, root: str, recursive: bool = True) -> List[MatchResult]:
        """
        Find all sensitive files in a directory.
        
        Args:
            root: Root directory to search
            recursive: Whether to search recursively
        
        Returns:
            List of MatchResult for all sensitive files found
        """
        matches = []
        
        try:
            if recursive:
                for dirpath, dirnames, filenames in os.walk(root):
                    for filename in filenames:
                        full_path = os.path.join(dirpath, filename)
                        rel_path = os.path.relpath(full_path, root)
                        
                        result = self.matches(rel_path)
                        if result.matched:
                            matches.append(result)
            else:
                for item in os.listdir(root):
                    full_path = os.path.join(root, item)
                    if os.path.isfile(full_path):
                        result = self.matches(item)
                        if result.matched:
                            matches.append(result)
        
        except (OSError, IOError) as e:
            logger.error(f"Error scanning directory '{root}': {e}")
        
        return matches

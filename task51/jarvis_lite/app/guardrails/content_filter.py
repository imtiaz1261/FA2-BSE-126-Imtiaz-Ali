"""
Content guardrails for filtering harmful/off-topic queries.
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)


class ContentFilter:
    """Filter harmful and off-topic content."""

    def __init__(self) -> None:
        """Initialize content filter with rules."""
        # Harmful patterns
        self.harmful_patterns = [
            # Violence
            r'\b(kill|murder|harm|hurt|abuse|assault)\b',
            # Illegal activities
            r'\b(hack|crack|steal|drugs|bomb|weapon)\b',
            # Self-harm
            r'\b(suicide|self-harm|self-hurt|overdose)\b',
            # Explicit content
            r'\b(porn|xxx|explicit|adult)\b',
            # Hate speech
            r'\b(hate|racist|sexist|discrimination)\b',
        ]

        # Off-topic keywords (for documentation/knowledge-base assistant)
        self.off_topic_patterns = [
            r'\b(dating|relationships|romance)\b',
            r'\b(politics|voting|elections)\b',
            r'\b(religion|atheism|faith)\b',
        ]

    def is_harmful(self, text: str) -> Tuple[bool, str]:
        """
        Check if content is harmful.
        
        Args:
            text: Text to check
            
        Returns:
            (is_harmful, reason)
        """
        text_lower = text.lower()
        
        for pattern in self.harmful_patterns:
            if re.search(pattern, text_lower):
                reason = f"Matched harmful pattern: {pattern}"
                logger.warning(f"Harmful content detected: {reason}")
                return True, reason
        
        return False, ""

    def is_off_topic(self, text: str) -> Tuple[bool, str]:
        """
        Check if query is off-topic for knowledge assistant.
        
        Args:
            text: Text to check
            
        Returns:
            (is_off_topic, reason)
        """
        text_lower = text.lower()
        
        for pattern in self.off_topic_patterns:
            if re.search(pattern, text_lower):
                reason = f"Matched off-topic pattern"
                logger.info(f"Off-topic query detected: {reason}")
                return True, reason
        
        return False, ""

    def is_injection_attempt(self, text: str) -> Tuple[bool, str]:
        """
        Check for prompt injection attacks.
        
        Args:
            text: Text to check
            
        Returns:
            (is_injection, reason)
        """
        # Check for suspicious prompt injection patterns
        injection_patterns = [
            r'ignore.*instructions',
            r'forget.*previous',
            r'system.*prompt',
            r'you.*are.*now',
            r'act.*as.*',
            r'pretend.*to.*be',
        ]
        
        text_lower = text.lower()
        
        for pattern in injection_patterns:
            if re.search(pattern, text_lower):
                logger.warning(f"Possible prompt injection detected: {pattern}")
                return True, f"Detected possible injection: {pattern}"
        
        return False, ""

    def filter_response(self, response: str) -> str:
        """
        Filter potentially harmful content from response.
        
        Args:
            response: Assistant response text
            
        Returns:
            Filtered response
        """
        # Simple filtering: remove explicit profanity
        profanities = [
            ("f**k", "****"),
            ("sh*t", "****"),
            ("a**hole", "****"),
        ]
        
        filtered = response
        for bad, replacement in profanities:
            filtered = filtered.replace(bad, replacement)
        
        return filtered

    def check_all(self, text: str) -> Tuple[bool, str]:
        """
        Run all checks on text.
        
        Args:
            text: Text to check
            
        Returns:
            (should_block, reason)
        """
        # Check for harmful content
        if self.is_harmful(text)[0]:
            return True, "Harmful content detected"
        
        # Check for injection attempts
        if self.is_injection_attempt(text)[0]:
            return True, "Possible prompt injection detected"
        
        # Check for off-topic (optional, depends on use case)
        # if self.is_off_topic(text)[0]:
        #     return True, "Query is off-topic for this assistant"
        
        return False, ""


class RateLimiter:
    """Simple rate limiting."""

    def __init__(self, max_requests: int = 100, window_minutes: int = 60) -> None:
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Max requests allowed
            window_minutes: Time window in minutes
        """
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests = {}  # user_id -> list of timestamps

    def is_rate_limited(self, user_id: str) -> bool:
        """Check if user is rate limited."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.window_minutes)
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests
        self.requests[user_id] = [t for t in self.requests[user_id] if t > cutoff]
        
        # Check if over limit
        if len(self.requests[user_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user: {user_id}")
            return True
        
        # Add current request
        self.requests[user_id].append(now)
        return False

    def get_remaining(self, user_id: str) -> int:
        """Get remaining requests for user."""
        if user_id not in self.requests:
            return self.max_requests
        
        from datetime import datetime, timedelta
        now = datetime.now()
        cutoff = now - timedelta(minutes=self.window_minutes)
        
        valid_requests = len([t for t in self.requests.get(user_id, []) if t > cutoff])
        return max(0, self.max_requests - valid_requests)

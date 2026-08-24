"""
Complete Safety Configuration System for Code Alpha

Manages all safety policies, limits, and configuration in a centralized way.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SafetyMode(str, Enum):
    """Safety enforcement modes."""
    PERMISSIVE = "permissive"  # Minimal restrictions
    STANDARD = "standard"  # Balanced safety
    STRICT = "strict"  # Maximum safety
    EMERGENCY = "emergency"  # Emergency lockdown


@dataclass
class SafetyLimits:
    """Configurable safety limits."""
    
    # Blast radius limits
    max_files_per_task: int = 50
    max_lines_per_task: int = 5000
    max_api_calls_per_task: int = 100
    max_shell_commands_per_task: int = 20
    max_database_queries_per_task: int = 50
    
    # Timing limits
    max_task_duration_minutes: int = 60
    approval_timeout_seconds: int = 3600
    
    # Resource limits
    max_concurrent_tasks: int = 5
    max_memory_per_task_gb: int = 4
    max_cpu_per_task_cores: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_mode(cls, mode: SafetyMode) -> 'SafetyLimits':
        """Create limits from safety mode."""
        if mode == SafetyMode.PERMISSIVE:
            return cls(
                max_files_per_task=200,
                max_lines_per_task=50000,
                max_api_calls_per_task=1000,
                max_shell_commands_per_task=100,
                max_database_queries_per_task=500,
                max_task_duration_minutes=240,
            )
        elif mode == SafetyMode.STRICT:
            return cls(
                max_files_per_task=20,
                max_lines_per_task=1000,
                max_api_calls_per_task=20,
                max_shell_commands_per_task=5,
                max_database_queries_per_task=10,
                max_task_duration_minutes=10,
            )
        elif mode == SafetyMode.EMERGENCY:
            return cls(
                max_files_per_task=1,
                max_lines_per_task=0,
                max_api_calls_per_task=0,
                max_shell_commands_per_task=0,
                max_database_queries_per_task=0,
                max_task_duration_minutes=1,
            )
        else:  # STANDARD
            return cls()


@dataclass
class SafetyPolicies:
    """Safety policies configuration."""
    
    # Hard-blocked actions
    blocked_actions: List[str] = None
    
    # Sensitive paths requiring approval
    sensitive_paths: List[str] = None
    
    # Auto-approval settings
    auto_approve_low_risk: bool = True
    auto_approve_for_owner: bool = False
    auto_approve_for_roles: List[str] = None
    
    # Approval settings
    require_approval_for_sensitive_paths: bool = True
    require_approval_for_blast_radius_exceeded: bool = True
    require_approval_for_database_modifications: bool = True
    require_approval_for_environment_changes: bool = True
    
    # Escalation settings
    escalation_enabled: bool = True
    escalation_chain: List[str] = None
    
    # Audit settings
    audit_enabled: bool = True
    audit_log_path: str = ".codealpha/audit.jsonl"
    audit_max_file_size_mb: int = 100
    audit_auto_rotate: bool = True
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.blocked_actions is None:
            self.blocked_actions = [
                "git_force_push",
                "git_branch_delete",
                "git_reset_hard",
                "file_delete_recursive",
            ]
        
        if self.sensitive_paths is None:
            self.sensitive_paths = [
                "**/auth/**",
                "**/billing/**",
                "**/infra/**",
                "**/.env*",
                "**/secret/**",
                ".github/workflows/**",
            ]
        
        if self.auto_approve_for_roles is None:
            self.auto_approve_for_roles = ["admin", "owner"]
        
        if self.escalation_chain is None:
            self.escalation_chain = [
                "slack_notification",
                "email_notification",
            ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SafetyConfig:
    """Complete safety configuration."""
    
    mode: SafetyMode = SafetyMode.STANDARD
    enabled: bool = True
    limits: SafetyLimits = None
    policies: SafetyPolicies = None
    
    # Notifications
    notify_on_approval_request: bool = True
    notify_on_approval_granted: bool = True
    notify_on_approval_rejected: bool = True
    notify_on_blocked_action: bool = True
    notify_on_blast_radius_warning: bool = True
    
    # Features
    enable_emergency_stop: bool = True
    enable_integrity_verification: bool = True
    enable_rate_limiting: bool = True
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.limits is None:
            self.limits = SafetyLimits.from_mode(self.mode)
        
        if self.policies is None:
            self.policies = SafetyPolicies()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mode': self.mode.value,
            'enabled': self.enabled,
            'limits': self.limits.to_dict(),
            'policies': self.policies.to_dict(),
            'notify_on_approval_request': self.notify_on_approval_request,
            'notify_on_approval_granted': self.notify_on_approval_granted,
            'notify_on_approval_rejected': self.notify_on_approval_rejected,
            'notify_on_blocked_action': self.notify_on_blocked_action,
            'notify_on_blast_radius_warning': self.notify_on_blast_radius_warning,
            'enable_emergency_stop': self.enable_emergency_stop,
            'enable_integrity_verification': self.enable_integrity_verification,
            'enable_rate_limiting': self.enable_rate_limiting,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SafetyConfig':
        """Create from dictionary."""
        mode = SafetyMode(data.get('mode', 'standard'))
        limits = SafetyLimits(**data.get('limits', {}))
        policies = SafetyPolicies(**data.get('policies', {}))
        
        return cls(
            mode=mode,
            enabled=data.get('enabled', True),
            limits=limits,
            policies=policies,
            notify_on_approval_request=data.get('notify_on_approval_request', True),
            notify_on_approval_granted=data.get('notify_on_approval_granted', True),
            notify_on_approval_rejected=data.get('notify_on_approval_rejected', True),
            notify_on_blocked_action=data.get('notify_on_blocked_action', True),
            notify_on_blast_radius_warning=data.get('notify_on_blast_radius_warning', True),
            enable_emergency_stop=data.get('enable_emergency_stop', True),
            enable_integrity_verification=data.get('enable_integrity_verification', True),
            enable_rate_limiting=data.get('enable_rate_limiting', True),
        )


class SafetyConfigManager:
    """Manages safety configuration lifecycle."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to config file (JSON or YAML)
        """
        self.config_path = Path(config_path) if config_path else None
        self.config = SafetyConfig()
        
        if self.config_path and self.config_path.exists():
            self.load()
    
    def load(self) -> None:
        """Load config from file."""
        if not self.config_path or not self.config_path.exists():
            logger.warning("Config file not found, using defaults")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            self.config = SafetyConfig.from_dict(data)
            logger.info(f"Loaded safety config from {self.config_path}")
        
        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.error(f"Error loading config file: {e}")
            logger.info("Using default configuration")
    
    def save(self) -> None:
        """Save config to file."""
        if not self.config_path:
            logger.warning("No config path specified")
            return
        
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            
            logger.info(f"Saved safety config to {self.config_path}")
        
        except IOError as e:
            logger.error(f"Error saving config file: {e}")
    
    def set_mode(self, mode: SafetyMode) -> None:
        """Change safety mode."""
        self.config.mode = mode
        self.config.limits = SafetyLimits.from_mode(mode)
        logger.info(f"Safety mode changed to {mode.value}")
    
    def get_config(self) -> SafetyConfig:
        """Get current config."""
        return self.config
    
    def update_limits(self, **kwargs) -> None:
        """Update limits."""
        for key, value in kwargs.items():
            if hasattr(self.config.limits, key):
                setattr(self.config.limits, key, value)
        
        logger.info(f"Updated safety limits: {kwargs}")
    
    def update_policies(self, **kwargs) -> None:
        """Update policies."""
        for key, value in kwargs.items():
            if hasattr(self.config.policies, key):
                setattr(self.config.policies, key, value)
        
        logger.info(f"Updated safety policies: {kwargs}")
    
    def enable_safety(self) -> None:
        """Enable safety."""
        self.config.enabled = True
        logger.info("Safety enabled")
    
    def disable_safety(self) -> None:
        """Disable safety (use with caution)."""
        self.config.enabled = False
        logger.warning("Safety disabled - agent has full access")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get config summary."""
        return {
            'mode': self.config.mode.value,
            'enabled': self.config.enabled,
            'blast_radius_limits': {
                'max_files': self.config.limits.max_files_per_task,
                'max_lines': self.config.limits.max_lines_per_task,
                'max_api_calls': self.config.limits.max_api_calls_per_task,
            },
            'approval_enabled': self.config.policies.require_approval_for_sensitive_paths,
            'audit_enabled': self.config.policies.audit_enabled,
            'emergency_stop_available': self.config.enable_emergency_stop,
        }


# Global config manager instance
_config_manager: Optional[SafetyConfigManager] = None


def get_safety_config() -> SafetyConfig:
    """Get the global safety configuration."""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = SafetyConfigManager()
    
    return _config_manager.get_config()


def get_config_manager() -> SafetyConfigManager:
    """Get the global config manager."""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = SafetyConfigManager()
    
    return _config_manager


def set_config_path(path: str) -> None:
    """Set the config file path."""
    global _config_manager
    _config_manager = SafetyConfigManager(config_path=path)

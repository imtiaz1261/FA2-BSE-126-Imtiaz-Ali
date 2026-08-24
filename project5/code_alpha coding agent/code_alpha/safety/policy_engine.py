"""
Policy Engine for Code Alpha Safety

Enforces hard-blocked actions and risk-based policies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk levels for actions."""
    BLOCKED = "blocked"  # Hard-blocked, cannot execute
    CRITICAL = "critical"  # Always requires approval
    HIGH = "high"  # Requires approval by default
    MEDIUM = "medium"  # May require approval based on context
    LOW = "low"  # Generally safe, auto-approved
    SAFE = "safe"  # Always safe


class ActionType(str, Enum):
    """Types of actions that can be evaluated."""
    GIT_FORCE_PUSH = "git_force_push"
    GIT_BRANCH_DELETE = "git_branch_delete"
    GIT_RESET_HARD = "git_reset_hard"
    FILE_DELETE_RECURSIVE = "file_delete_recursive"
    FILE_EDIT = "file_edit"
    FILE_READ = "file_read"
    SHELL_COMMAND = "shell_command"
    API_CALL = "api_call"
    DATABASE_MODIFY = "database_modify"
    ENVIRONMENT_EDIT = "environment_edit"
    CI_CONFIG_EDIT = "ci_config_edit"
    FILESYSTEM_ACCESS = "filesystem_access"


@dataclass
class ActionContext:
    """Context for action evaluation."""
    
    action_type: ActionType
    target: str  # File path, command, etc.
    repo_root: str
    task_id: str
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ActionEvaluation:
    """Result of action evaluation."""
    
    action_type: ActionType
    target: str
    risk_level: RiskLevel
    is_blocked: bool
    requires_approval: bool
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'action_type': self.action_type.value,
            'target': self.target,
            'risk_level': self.risk_level.value,
            'is_blocked': self.is_blocked,
            'requires_approval': self.requires_approval,
            'reason': self.reason,
            'timestamp': self.timestamp,
        }


class PolicyEngine:
    """
    Enforces safety policies for Code Alpha.
    
    Hard-blocks dangerous actions and routes sensitive operations
    through approval workflows.
    """
    
    def __init__(
        self,
        blocked_actions: Optional[Set[ActionType]] = None,
        sensitive_patterns: Optional[List[str]] = None,
        auto_approve_low_risk: bool = True,
    ):
        """
        Initialize policy engine.
        
        Args:
            blocked_actions: Hard-blocked action types
            sensitive_patterns: Path patterns requiring approval
            auto_approve_low_risk: Auto-approve low-risk actions
        """
        # Hard-blocked actions (cannot be overridden)
        self.blocked_actions = blocked_actions or {
            ActionType.GIT_FORCE_PUSH,
            ActionType.GIT_BRANCH_DELETE,
            ActionType.GIT_RESET_HARD,
            ActionType.FILE_DELETE_RECURSIVE,
        }
        
        self.sensitive_patterns = sensitive_patterns or []
        self.auto_approve_low_risk = auto_approve_low_risk
        
        # Risk assessment rules
        self.risk_rules = self._build_risk_rules()
        
        logger.info(f"PolicyEngine initialized with {len(self.blocked_actions)} blocked actions")
    
    def evaluate(self, context: ActionContext) -> ActionEvaluation:
        """
        Evaluate an action against safety policies.
        
        Returns ActionEvaluation with risk assessment and approval requirements.
        """
        # Check if action is hard-blocked
        if context.action_type in self.blocked_actions:
            logger.warning(
                f"Hard-blocked action detected: {context.action_type} on {context.target}",
                extra={'task_id': context.task_id}
            )
            return ActionEvaluation(
                action_type=context.action_type,
                target=context.target,
                risk_level=RiskLevel.BLOCKED,
                is_blocked=True,
                requires_approval=False,
                reason=f"Action type '{context.action_type.value}' is hard-blocked",
            )
        
        # Determine risk level
        risk_level = self._assess_risk(context)
        
        # Determine if approval is required
        requires_approval = self._requires_approval(context, risk_level)
        
        reason = self._generate_reason(context, risk_level)
        
        evaluation = ActionEvaluation(
            action_type=context.action_type,
            target=context.target,
            risk_level=risk_level,
            is_blocked=False,
            requires_approval=requires_approval,
            reason=reason,
        )
        
        log_level = logging.WARNING if requires_approval else logging.INFO
        logger.log(
            log_level,
            f"Action evaluated: {context.action_type} - Risk: {risk_level}, "
            f"Approval required: {requires_approval}",
            extra={'task_id': context.task_id}
        )
        
        return evaluation
    
    def _assess_risk(self, context: ActionContext) -> RiskLevel:
        """Assess risk level of an action."""
        # Check against risk rules
        for action_type, default_risk in self.risk_rules.items():
            if context.action_type == action_type:
                # Check for sensitive patterns
                if self._matches_sensitive_pattern(context.target):
                    return RiskLevel.CRITICAL
                
                return default_risk
        
        # Default risk
        return RiskLevel.MEDIUM
    
    def _requires_approval(self, context: ActionContext, risk_level: RiskLevel) -> bool:
        """Determine if approval is required."""
        if risk_level == RiskLevel.BLOCKED:
            return False
        
        if risk_level == RiskLevel.CRITICAL:
            return True
        
        if risk_level == RiskLevel.HIGH:
            return True
        
        if risk_level == RiskLevel.SAFE:
            return False
        
        if risk_level == RiskLevel.LOW:
            # If auto-approve is disabled, LOW risk requires approval
            return not self.auto_approve_low_risk
        
        return risk_level == RiskLevel.MEDIUM
    
    def _matches_sensitive_pattern(self, target: str) -> bool:
        """Check if target matches sensitive path patterns."""
        from fnmatch import fnmatch
        
        for pattern in self.sensitive_patterns:
            if fnmatch(target.lower(), pattern.lower()):
                return True
        
        return False
    
    def _generate_reason(self, context: ActionContext, risk_level: RiskLevel) -> str:
        """Generate human-readable reason for evaluation."""
        if self._matches_sensitive_pattern(context.target):
            return f"Target matches sensitive path pattern (Risk: {risk_level.value})"
        
        reason_map = {
            RiskLevel.BLOCKED: f"Action type '{context.action_type.value}' is hard-blocked",
            RiskLevel.CRITICAL: "Action involves critical systems requiring approval",
            RiskLevel.HIGH: "High-risk action requires approval",
            RiskLevel.MEDIUM: "Medium-risk action - approval may be required",
            RiskLevel.LOW: "Low-risk action - auto-approved",
            RiskLevel.SAFE: "Safe action - no approval required",
        }
        
        return reason_map.get(risk_level, "Unknown risk")
    
    def _build_risk_rules(self) -> Dict[ActionType, RiskLevel]:
        """Build risk assessment rules."""
        return {
            # File operations
            ActionType.FILE_EDIT: RiskLevel.LOW,
            ActionType.FILE_READ: RiskLevel.SAFE,
            ActionType.FILE_DELETE_RECURSIVE: RiskLevel.BLOCKED,
            
            # Git operations
            ActionType.GIT_FORCE_PUSH: RiskLevel.BLOCKED,
            ActionType.GIT_BRANCH_DELETE: RiskLevel.BLOCKED,
            ActionType.GIT_RESET_HARD: RiskLevel.BLOCKED,
            
            # Shell commands
            ActionType.SHELL_COMMAND: RiskLevel.MEDIUM,
            
            # API calls
            ActionType.API_CALL: RiskLevel.LOW,
            
            # Database
            ActionType.DATABASE_MODIFY: RiskLevel.HIGH,
            
            # Configuration
            ActionType.ENVIRONMENT_EDIT: RiskLevel.CRITICAL,
            ActionType.CI_CONFIG_EDIT: RiskLevel.CRITICAL,
            
            # Filesystem
            ActionType.FILESYSTEM_ACCESS: RiskLevel.LOW,
        }
    
    def set_blocked_actions(self, actions: Set[ActionType]) -> None:
        """Update blocked actions (hard enforcement list)."""
        self.blocked_actions = actions
        logger.info(f"Blocked actions updated: {len(actions)} actions")
    
    def add_sensitive_pattern(self, pattern: str) -> None:
        """Add a sensitive path pattern."""
        if pattern not in self.sensitive_patterns:
            self.sensitive_patterns.append(pattern)
            logger.info(f"Added sensitive pattern: {pattern}")
    
    def remove_sensitive_pattern(self, pattern: str) -> None:
        """Remove a sensitive path pattern."""
        if pattern in self.sensitive_patterns:
            self.sensitive_patterns.remove(pattern)
            logger.info(f"Removed sensitive pattern: {pattern}")
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of current policies."""
        return {
            'blocked_actions': [a.value for a in self.blocked_actions],
            'sensitive_patterns': self.sensitive_patterns,
            'auto_approve_low_risk': self.auto_approve_low_risk,
            'total_blocked': len(self.blocked_actions),
            'total_sensitive_patterns': len(self.sensitive_patterns),
        }

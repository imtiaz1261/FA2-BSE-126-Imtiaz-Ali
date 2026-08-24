"""
Safety, Guardrails & Human-in-the-Loop Controls for Code Alpha

Provides:
- Hard-blocked action enforcement
- Risk-based approval workflow
- Sensitive path protection
- Append-only audit logging
- Blast radius limiting
- Comprehensive safety configuration
"""

from .policy_engine import (
    PolicyEngine, ActionEvaluation, RiskLevel, ActionType, ActionContext
)
from .path_matcher import PathMatcher, MatchResult, MatchType
from .audit_logger import AuditLogger, AuditLogEntry, AuditLogLevel
from .blast_radius import BlastRadiusLimiter, BlastRadiusMetrics, BlastRadiusStatus
from .approval_gateway import ApprovalGateway, ApprovalRequest, ApprovalStatus
from .sandbox_integration import (
    SandboxIntegration, ToolCall, ToolCallResult, ToolType,
    get_sandbox_integration, reset_sandbox_integration
)
from .safety_config import (
    SafetyConfig, SafetyConfigManager, SafetyLimits, SafetyPolicies, SafetyMode,
    get_safety_config, get_config_manager, set_config_path
)
from .models import SafetyAction, AuditEntry
from .config import DEFAULT_BLOCKED_ACTIONS, DEFAULT_SENSITIVE_PATHS

__all__ = [
    'PolicyEngine',
    'PathMatcher',
    'AuditLogger',
    'BlastRadiusLimiter',
    'ApprovalGateway',
    'SandboxIntegration',
    'SafetyConfig',
    'SafetyConfigManager',
    'SafetyAction',
    'ActionEvaluation',
    'RiskLevel',
    'MatchResult',
    'ActionType',
    'ActionContext',
    'MatchType',
    'AuditLogEntry',
    'AuditLogLevel',
    'BlastRadiusMetrics',
    'BlastRadiusStatus',
    'ApprovalRequest',
    'ApprovalStatus',
    'ToolCall',
    'ToolCallResult',
    'ToolType',
    'SafetyLimits',
    'SafetyPolicies',
    'SafetyMode',
    'AuditEntry',
    'DEFAULT_BLOCKED_ACTIONS',
    'DEFAULT_SENSITIVE_PATHS',
    'get_sandbox_integration',
    'reset_sandbox_integration',
    'get_safety_config',
    'get_config_manager',
    'set_config_path',
]

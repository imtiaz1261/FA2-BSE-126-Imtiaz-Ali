"""
Default safety configuration for Code Alpha
"""

from typing import Set, List

# Hard-blocked actions (cannot be overridden)
DEFAULT_BLOCKED_ACTIONS: Set[str] = {
    "git_force_push",
    "git_branch_delete",
    "git_reset_hard",
    "file_delete_recursive",
    "rm_recursive",
    "edit_secrets",
    "edit_ci_config",
    "filesystem_outside_repo",
}

# Sensitive path patterns (always require approval)
DEFAULT_SENSITIVE_PATHS: List[str] = [
    # Authentication & Authorization
    "**/auth/**",
    "**/authentication/**",
    "**/permission/**",
    "**/oauth/**",
    
    # Payment & Billing
    "**/billing/**",
    "**/payment/**",
    "**/stripe/**",
    "**/invoice/**",
    
    # Infrastructure & DevOps
    "**/infra/**",
    "**/infrastructure/**",
    "**/terraform/**",
    "**/ansible/**",
    "**/kubernetes/**",
    "**/docker/**",
    
    # Secrets & Credentials
    "**/secret/**",
    "**/credentials/**",
    "**/.env",
    "**/.env.*",
    "**/secrets.json",
    "**/credentials.json",
    "**/*.pem",
    "**/*.key",
    "**/*.crt",
    "**/*.pfx",
    
    # Configuration
    "**/config/prod/**",
    "**/config/production/**",
    "**/settings/prod/**",
    
    # CI/CD
    ".github/workflows/**",
    ".github/actions/**",
    ".gitlab-ci.yml",
    ".gitlab-ci/**",
    "Jenkinsfile",
    ".circleci/config.yml",
    
    # Database
    "**/migrations/**",
    "**/schema/**",
    "sql/production/**",
    
    # Security
    "**/security/**",
    "**/ssl/**",
    "**/tls/**",
    "**/certificates/**",
]

# Default blocked file extensions
DEFAULT_BLOCKED_EXTENSIONS: Set[str] = {
    ".env",
    ".pem",
    ".key",
    ".crt",
    ".pfx",
    ".p12",
    ".jks",
    ".keystore",
    ".credentials",
    ".token",
    ".secret",
    ".password",
}

# Default safety limits
DEFAULT_BLAST_RADIUS_LIMITS = {
    "max_files_per_task": 50,
    "max_lines_per_task": 5000,
    "max_api_calls_per_task": 100,
    "max_shell_commands_per_task": 20,
    "max_database_queries_per_task": 50,
}

# Approval timeout
DEFAULT_APPROVAL_TIMEOUT_SECONDS = 3600  # 1 hour

# Risk level mapping
RISK_LEVEL_NAMES = {
    "blocked": "Hard-Blocked",
    "critical": "Critical - Requires Approval",
    "high": "High-Risk - Requires Approval",
    "medium": "Medium-Risk - May Require Approval",
    "low": "Low-Risk - Auto-Approved",
    "safe": "Safe - No Approval Needed",
}

# Action descriptions for audit log
ACTION_DESCRIPTIONS = {
    "git_force_push": "Force push to git repository",
    "git_branch_delete": "Delete git branch",
    "git_reset_hard": "Hard reset git history",
    "file_delete_recursive": "Recursively delete files",
    "file_edit": "Edit file",
    "file_read": "Read file",
    "shell_command": "Execute shell command",
    "api_call": "Make API call",
    "database_query": "Execute database query",
    "environment_edit": "Edit environment configuration",
    "ci_config_edit": "Edit CI/CD configuration",
}

# Default escalation chain
DEFAULT_ESCALATION_CHAIN = [
    "slack_notification",
    "email_notification",
    "pagerduty_escalation",
]

# Sensitive role names (for human approval)
SENSITIVE_ROLES = {
    "admin",
    "security",
    "devops",
    "compliance",
}

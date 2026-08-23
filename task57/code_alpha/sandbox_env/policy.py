import re
from dataclasses import dataclass, field

# Only these registries can ever be allow-listed — this is a hard ceiling,
# not something a task or agent can widen at runtime.
KNOWN_REGISTRIES = {
    "pypi": re.compile(r"^pip\s+install\b"),
    "npm": re.compile(r"^npm\s+(install|i)\b"),
}

# Commands that are never allowed regardless of policy — these bypass the
# sandbox's isolation model entirely (mount manipulation, privilege escalation).
DENYLIST_PATTERNS = [
    re.compile(r"\bsudo\b"),
    re.compile(r"\bmount\b"),
    re.compile(r"\bchmod\s+777\b"),
    re.compile(r"/dev/(sd|nvme)"),
    re.compile(r"\bdd\s+if="),
]


@dataclass
class SecurityPolicy:
    """One policy per session. Defaults are deny-by-default: no network,
    tight resource caps, no registries allowed until explicitly granted."""
    cpu_seconds: int = 30            # RLIMIT_CPU — wall CPU time per command
    memory_mb: int = 512              # RLIMIT_AS cap
    timeout_seconds: int = 60          # wall-clock kill timeout per command
    disk_quota_mb: int = 1024          # cap on total sandbox working-dir size
    network_default_deny: bool = True
    allowed_registries: set = field(default_factory=set)  # subset of KNOWN_REGISTRIES

    def allow_registry(self, name: str) -> None:
        if name not in KNOWN_REGISTRIES:
            raise ValueError(f"unknown registry: {name} (must be one of {list(KNOWN_REGISTRIES)})")
        self.allowed_registries.add(name)


class PolicyViolation(Exception):
    pass


def check_command(command: str, policy: SecurityPolicy) -> None:
    """Raises PolicyViolation if `command` isn't allowed under `policy`.
    Called on every run_command before it ever reaches a container/process."""
    for pattern in DENYLIST_PATTERNS:
        if pattern.search(command):
            raise PolicyViolation(f"command matches denylisted pattern: {pattern.pattern!r}")

    for registry, pattern in KNOWN_REGISTRIES.items():
        if pattern.search(command) and registry not in policy.allowed_registries:
            raise PolicyViolation(
                f"command requires network access to {registry!r}, which is not "
                f"in this session's allow-list ({sorted(policy.allowed_registries)}). "
                f"Call policy.allow_registry({registry!r}) first if this install is approved."
            )

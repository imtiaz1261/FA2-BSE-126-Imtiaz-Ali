"""
Docker sandbox manager for isolated code execution.

Provides ephemeral, resource-limited containers for agent code execution.
Uses gVisor runtime for enhanced security (if available).
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class SandboxConfig:
    """Sandbox resource limits and configuration."""

    memory_limit_mb: int = 512  # Max memory
    cpu_limit: float = 1.0  # CPU cores
    timeout_seconds: int = 300  # Max execution time
    network_disabled: bool = True  # No network access
    image: str = "python:3.11-slim"  # Base Docker image
    runtime: str = "runc"  # Docker runtime (runc or gvisor if available)


# ============================================================================
# Sandbox Container
# ============================================================================


class SandboxContainer:
    """Manages a single isolated container."""

    def __init__(
        self,
        session_id: str,
        repo_path: str,
        config: Optional[SandboxConfig] = None,
    ):
        """
        Initialize sandbox container.

        Args:
            session_id: Unique session identifier
            repo_path: Path to repository to mount (read-only)
            config: Sandbox configuration (uses defaults if None)
        """
        self.session_id = session_id
        self.repo_path = Path(repo_path).resolve()
        self.config = config or SandboxConfig()
        self.container_id: Optional[str] = None
        self.work_dir = "/workspace"
        self.is_running = False

    async def start(self) -> bool:
        """
        Start the sandbox container.

        Returns:
            True if started successfully
        """
        try:
            # Build Docker run command
            cmd = [
                "docker",
                "run",
                "-d",  # Detached
                "--rm",  # Auto-remove on exit
                f"--name={self._container_name()}",
                f"--memory={self.config.memory_limit_mb}m",
                f"--cpus={self.config.cpu_limit}",
                "--pids-limit=100",  # Prevent fork bombs
                "--read-only",  # Filesystem read-only by default
                "--tmpfs=/tmp:size=100m",  # Writable temp
                "--tmpfs=/home:size=100m",  # Writable home
            ]

            # Mount repository (read-only)
            cmd.extend(["-v", f"{self.repo_path}:{self.work_dir}:ro"])

            # Disable network (unless needed)
            if self.config.network_disabled:
                cmd.append("--network=none")

            # Runtime (gvisor if available, fall back to runc)
            if self.config.runtime == "gvisor":
                cmd.extend(["--runtime=runsc"])

            # Image and init command
            cmd.extend([self.config.image, "sleep", "3600"])  # Keep alive for 1 hour

            # Run command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"Failed to start container: {result.stderr}")
                return False

            self.container_id = result.stdout.strip()
            self.is_running = True

            logger.info(
                f"Started sandbox container {self.container_id} "
                f"for session {self.session_id}"
            )

            return True

        except Exception as e:
            logger.error(f"Container start error: {e}")
            return False

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: str = "/workspace",
    ) -> "ExecutionResult":
        """
        Execute command in container.

        Args:
            command: Command to execute
            timeout: Override default timeout
            cwd: Working directory inside container

        Returns:
            ExecutionResult with stdout, stderr, exit code
        """
        if not self.is_running or not self.container_id:
            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr="Container not running",
                duration=0,
            )

        timeout_secs = timeout or self.config.timeout_seconds
        start_time = time.time()

        try:
            # Execute in container
            cmd = [
                "docker",
                "exec",
                "-w",
                cwd,
                self.container_id,
                "/bin/bash",
                "-c",
                command,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_secs,
            )

            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.warning(f"Command timeout after {duration}s: {command}")

            return ExecutionResult(
                exit_code=124,  # Standard timeout exit code
                stdout="",
                stderr=f"Command timeout after {timeout_secs}s",
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Execution error: {e}")

            return ExecutionResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
                duration=duration,
            )

    async def stop(self) -> bool:
        """
        Stop and remove the container.

        Returns:
            True if stopped successfully
        """
        if not self.container_id:
            return True

        try:
            cmd = ["docker", "stop", self.container_id]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self.is_running = False
                logger.info(f"Stopped container {self.container_id}")
                return True
            else:
                logger.warning(f"Failed to stop container: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Container stop error: {e}")
            return False

    def _container_name(self) -> str:
        """Generate container name."""
        return f"sandbox-{self.session_id}".replace("_", "-")[:63]


# ============================================================================
# Execution Result
# ============================================================================


@dataclass
class ExecutionResult:
    """Result of command execution in sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    duration: float

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "success": self.success,
        }


# ============================================================================
# Sandbox Manager
# ============================================================================


class SandboxManager:
    """Manage sandbox containers for agent sessions."""

    def __init__(self):
        """Initialize sandbox manager."""
        self.containers: dict[str, SandboxContainer] = {}

    async def create_container(
        self,
        session_id: str,
        repo_path: str,
        config: Optional[SandboxConfig] = None,
    ) -> Optional[SandboxContainer]:
        """
        Create and start a sandbox container.

        Args:
            session_id: Unique session ID
            repo_path: Repository path to mount
            config: Sandbox configuration

        Returns:
            Started container or None if failed
        """
        try:
            container = SandboxContainer(session_id, repo_path, config)

            if not await container.start():
                return None

            self.containers[session_id] = container
            return container

        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            return None

    async def get_container(self, session_id: str) -> Optional[SandboxContainer]:
        """Get container for session."""
        return self.containers.get(session_id)

    async def destroy_container(self, session_id: str) -> bool:
        """
        Destroy container and clean up.

        Args:
            session_id: Session ID

        Returns:
            True if destroyed successfully
        """
        container = self.containers.pop(session_id, None)

        if not container:
            return True

        success = await container.stop()

        if success:
            logger.info(f"Destroyed sandbox for session {session_id}")

        return success

    async def cleanup_all(self) -> None:
        """Clean up all containers."""
        for session_id in list(self.containers.keys()):
            await self.destroy_container(session_id)


# ============================================================================
# Global Manager
# ============================================================================

_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """Get or create global sandbox manager."""
    global _sandbox_manager

    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()

    return _sandbox_manager

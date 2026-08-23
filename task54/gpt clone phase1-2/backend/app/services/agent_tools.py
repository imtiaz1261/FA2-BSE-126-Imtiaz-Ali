"""
Agent tools for code manipulation and execution.

Tools: file_read, file_write (staged), shell_exec, git_diff, list_files
All tools are scoped to a repository workspace.
"""

import difflib
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.services.docker_sandbox import SandboxContainer, ExecutionResult

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Result
# ============================================================================


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
        }


# ============================================================================
# Agent Tools
# ============================================================================


class AgentTools:
    """Tools available to the coding agent."""

    def __init__(
        self,
        repo_path: str,
        sandbox: SandboxContainer,
    ):
        """
        Initialize agent tools.

        Args:
            repo_path: Root path of repository (local)
            sandbox: Sandbox container for execution
        """
        self.repo_path = Path(repo_path).resolve()
        self.sandbox = sandbox
        self.staged_changes: dict[str, dict] = {}  # path -> {operation, content}

    # ========================================================================
    # File Operations
    # ========================================================================

    def file_read(self, file_path: str) -> ToolResult:
        """
        Read a file from the repository.

        Args:
            file_path: Path relative to repo root

        Returns:
            ToolResult with file content
        """
        try:
            full_path = (self.repo_path / file_path).resolve()

            # Security: ensure path is within repo
            if not str(full_path).startswith(str(self.repo_path)):
                return ToolResult(
                    success=False,
                    output="",
                    error="Path traversal not allowed",
                )

            if not full_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {file_path}",
                )

            content = full_path.read_text(encoding="utf-8")

            return ToolResult(
                success=True,
                output=content,
            )

        except Exception as e:
            logger.error(f"File read error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    def file_write(
        self,
        file_path: str,
        content: str,
        operation: str = "update",
    ) -> ToolResult:
        """
        Stage a file write (doesn't actually write yet).

        Args:
            file_path: Path relative to repo root
            content: New file content
            operation: 'create', 'update', or 'delete'

        Returns:
            ToolResult with diff
        """
        try:
            full_path = (self.repo_path / file_path).resolve()

            # Security: ensure path is within repo
            if not str(full_path).startswith(str(self.repo_path)):
                return ToolResult(
                    success=False,
                    output="",
                    error="Path traversal not allowed",
                )

            # Get original content for diff
            original_content = ""
            if full_path.exists():
                original_content = full_path.read_text(encoding="utf-8")

            # Generate diff
            if operation == "delete":
                diff_lines = list(
                    difflib.unified_diff(
                        original_content.splitlines(keepends=True),
                        [],
                        fromfile=f"a/{file_path}",
                        tofile=f"b/{file_path}",
                    )
                )
                diff = "".join(diff_lines)
            elif operation == "create":
                diff_lines = list(
                    difflib.unified_diff(
                        [],
                        content.splitlines(keepends=True),
                        fromfile=f"a/{file_path}",
                        tofile=f"b/{file_path}",
                    )
                )
                diff = "".join(diff_lines)
            else:  # update
                diff_lines = list(
                    difflib.unified_diff(
                        original_content.splitlines(keepends=True),
                        content.splitlines(keepends=True),
                        fromfile=f"a/{file_path}",
                        tofile=f"b/{file_path}",
                    )
                )
                diff = "".join(diff_lines)

            # Stage the change
            self.staged_changes[file_path] = {
                "operation": operation,
                "original_content": original_content,
                "proposed_content": content if operation != "delete" else None,
                "diff": diff,
            }

            return ToolResult(
                success=True,
                output=diff or f"File {operation}d: {file_path}",
            )

        except Exception as e:
            logger.error(f"File write staging error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    def list_files(self, directory: str = ".") -> ToolResult:
        """
        List files in a directory.

        Args:
            directory: Directory path relative to repo root

        Returns:
            ToolResult with file list
        """
        try:
            dir_path = (self.repo_path / directory).resolve()

            if not str(dir_path).startswith(str(self.repo_path)):
                return ToolResult(
                    success=False,
                    output="",
                    error="Path traversal not allowed",
                )

            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Not a directory: {directory}",
                )

            files = []
            for item in sorted(dir_path.iterdir()):
                if item.is_file():
                    files.append(f"  {item.name} (file)")
                elif item.is_dir() and not item.name.startswith("."):
                    files.append(f"  {item.name}/ (dir)")

            output = f"Contents of {directory}:\n" + "\n".join(files)

            return ToolResult(success=True, output=output)

        except Exception as e:
            logger.error(f"List files error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    # ========================================================================
    # Execution Tools
    # ========================================================================

    async def shell_exec(self, command: str, cwd: str = "/workspace") -> ToolResult:
        """
        Execute a shell command in the sandbox.

        Args:
            command: Command to execute
            cwd: Working directory inside sandbox

        Returns:
            ToolResult with stdout/stderr
        """
        try:
            result = await self.sandbox.execute(command, cwd=cwd)

            output = result.stdout

            if result.stderr:
                output = f"{output}\n[stderr]\n{result.stderr}"

            if result.success:
                return ToolResult(success=True, output=output)
            else:
                return ToolResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr or f"Exit code: {result.exit_code}",
                )

        except Exception as e:
            logger.error(f"Shell execution error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    async def run_tests(self, command: str = "pytest") -> ToolResult:
        """
        Run tests in the sandbox.

        Args:
            command: Test command (default: pytest)

        Returns:
            ToolResult with test output
        """
        return await self.shell_exec(f"{command} -v")

    # ========================================================================
    # Git Tools
    # ========================================================================

    def git_diff(self, staged_only: bool = True) -> ToolResult:
        """
        Get diff of staged changes.

        Args:
            staged_only: Include only staged changes or all

        Returns:
            ToolResult with diff output
        """
        try:
            if not self.staged_changes:
                return ToolResult(
                    success=True,
                    output="No staged changes",
                )

            diffs = []
            for file_path, change in self.staged_changes.items():
                diffs.append(change["diff"])

            output = "\n".join(diffs)

            return ToolResult(success=True, output=output)

        except Exception as e:
            logger.error(f"Git diff error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    def get_staged_changes(self) -> dict:
        """Get all staged changes."""
        return dict(self.staged_changes)

    def apply_staged_changes(self) -> ToolResult:
        """
        Apply all staged changes to files.

        Should be called after user approval.

        Returns:
            ToolResult indicating success
        """
        try:
            for file_path, change in self.staged_changes.items():
                full_path = (self.repo_path / file_path).resolve()

                # Security check
                if not str(full_path).startswith(str(self.repo_path)):
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Path traversal not allowed: {file_path}",
                    )

                if change["operation"] == "delete":
                    full_path.unlink()
                else:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(change["proposed_content"], encoding="utf-8")

            self.staged_changes.clear()

            return ToolResult(success=True, output="Changes applied")

        except Exception as e:
            logger.error(f"Apply staged changes error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )

    def revert_staged_changes(self) -> ToolResult:
        """Revert all staged changes."""
        self.staged_changes.clear()
        return ToolResult(success=True, output="Staged changes reverted")

    # ========================================================================
    # Tool Registry
    # ========================================================================

    def get_tools(self) -> dict[str, Any]:
        """Get all available tools as a dictionary."""
        return {
            "file_read": {
                "description": "Read a file from the repository",
                "params": {"file_path": "Path relative to repo root"},
            },
            "file_write": {
                "description": "Stage a file write (create, update, or delete)",
                "params": {
                    "file_path": "Path relative to repo root",
                    "content": "New file content",
                    "operation": "create, update, or delete",
                },
            },
            "list_files": {
                "description": "List files in a directory",
                "params": {"directory": "Directory path relative to repo root"},
            },
            "shell_exec": {
                "description": "Execute a shell command in sandbox",
                "params": {"command": "Command to execute"},
            },
            "run_tests": {
                "description": "Run tests",
                "params": {"command": "Test command (default: pytest)"},
            },
            "git_diff": {
                "description": "Get diff of staged changes",
                "params": {},
            },
        }

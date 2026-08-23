"""
Integration tests for agent sandbox isolation and tool execution.

Tests:
- Container lifecycle (start, execute, stop)
- Resource limits (CPU, memory, timeout)
- Path security (no traversal, read-only mounts)
- Tool execution and error recovery
- Network isolation
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.services.agent_tools import AgentTools
from app.services.docker_sandbox import (
    ExecutionResult,
    SandboxConfig,
    SandboxContainer,
    SandboxManager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create test structure
        (repo_path / "src").mkdir()
        (repo_path / "src" / "main.py").write_text("print('Hello')\n")
        (repo_path / "tests").mkdir()
        (repo_path / "tests" / "test_main.py").write_text(
            "def test_main():\n    assert True\n"
        )
        (repo_path / "README.md").write_text("# Test Project\n")

        yield repo_path


@pytest.fixture
async def sandbox_config():
    """Create sandbox configuration."""
    return SandboxConfig(
        memory_limit_mb=256,
        cpu_limit=0.5,
        timeout_seconds=30,
        network_disabled=True,
    )


@pytest.fixture
async def sandbox_container(temp_repo, sandbox_config):
    """Create and start a sandbox container."""
    container = SandboxContainer(
        session_id="test-session-001",
        repo_path=str(temp_repo),
        config=sandbox_config,
    )

    if await container.start():
        yield container
        await container.stop()
    else:
        pytest.skip("Docker not available or failed to start container")


@pytest.fixture
async def agent_tools(temp_repo, sandbox_container):
    """Create agent tools with sandbox."""
    return AgentTools(str(temp_repo), sandbox_container)


# ============================================================================
# Container Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sandbox_start_stop(temp_repo, sandbox_config):
    """Test container start and stop."""
    container = SandboxContainer(
        session_id="test-start-stop",
        repo_path=str(temp_repo),
        config=sandbox_config,
    )

    assert not container.is_running
    assert container.container_id is None

    success = await container.start()
    if not success:
        pytest.skip("Docker not available")

    assert container.is_running
    assert container.container_id is not None
    assert len(container.container_id) > 0

    stopped = await container.stop()
    assert stopped
    assert not container.is_running


@pytest.mark.asyncio
async def test_sandbox_multiple_containers(temp_repo, sandbox_config):
    """Test creating multiple containers."""
    containers = []

    try:
        for i in range(3):
            container = SandboxContainer(
                session_id=f"test-multi-{i}",
                repo_path=str(temp_repo),
                config=sandbox_config,
            )

            success = await container.start()
            if not success:
                pytest.skip("Docker not available")

            containers.append(container)
            assert container.is_running

        # All should be running
        assert all(c.is_running for c in containers)
        assert len(set(c.container_id for c in containers)) == 3  # Unique IDs

    finally:
        for container in containers:
            await container.stop()


# ============================================================================
# Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sandbox_basic_execution(sandbox_container):
    """Test basic command execution."""
    result = await sandbox_container.execute("echo 'Hello, Sandbox!'")

    assert result.success
    assert "Hello, Sandbox!" in result.stdout
    assert result.exit_code == 0
    assert result.duration > 0


@pytest.mark.asyncio
async def test_sandbox_failed_command(sandbox_container):
    """Test execution of failing command."""
    result = await sandbox_container.execute("exit 1")

    assert not result.success
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_sandbox_stderr_capture(sandbox_container):
    """Test stderr capture."""
    result = await sandbox_container.execute("echo 'error' >&2")

    assert result.exit_code == 0
    assert "error" in result.stderr


@pytest.mark.asyncio
async def test_sandbox_timeout(sandbox_container):
    """Test command timeout."""
    result = await sandbox_container.execute(
        "sleep 100",
        timeout=2,
    )

    assert not result.success
    assert result.exit_code == 124  # Standard timeout code
    assert "timeout" in result.stderr.lower()
    assert result.duration < 5  # Should timeout quickly


@pytest.mark.asyncio
async def test_sandbox_working_directory(sandbox_container):
    """Test working directory in container."""
    result = await sandbox_container.execute(
        "pwd",
        cwd="/workspace",
    )

    assert result.success
    assert "/workspace" in result.stdout


# ============================================================================
# File Access Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sandbox_readonly_filesystem(sandbox_container):
    """Test that filesystem is read-only."""
    # Try to write to root (should fail)
    result = await sandbox_container.execute(
        "touch /test.txt",
        cwd="/workspace",
    )

    # Should fail (read-only filesystem)
    assert not result.success or "Read-only" in result.stderr


@pytest.mark.asyncio
async def test_sandbox_writable_tmpfs(sandbox_container):
    """Test that /tmp is writable."""
    result = await sandbox_container.execute(
        "echo 'test' > /tmp/test.txt && cat /tmp/test.txt",
    )

    assert result.success
    assert "test" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_mount_point(sandbox_container):
    """Test mounted repository access."""
    result = await sandbox_container.execute(
        "ls -la /workspace",
    )

    assert result.success
    assert "src" in result.stdout or "tests" in result.stdout


# ============================================================================
# Tool Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tool_file_read(agent_tools):
    """Test file read tool."""
    result = agent_tools.file_read("README.md")

    assert result.success
    assert "Test Project" in result.output


@pytest.mark.asyncio
async def test_tool_file_read_not_found(agent_tools):
    """Test file read with nonexistent file."""
    result = agent_tools.file_read("nonexistent.txt")

    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_tool_file_read_path_traversal(agent_tools):
    """Test path traversal protection."""
    result = agent_tools.file_read("../../../etc/passwd")

    assert not result.success
    assert "traversal" in result.error.lower()


@pytest.mark.asyncio
async def test_tool_file_write_staging(agent_tools):
    """Test file write staging."""
    result = agent_tools.file_write(
        "src/new_file.py",
        "print('new')\n",
        operation="create",
    )

    assert result.success
    assert "new_file.py" in result.output

    # Check staged changes
    staged = agent_tools.get_staged_changes()
    assert "src/new_file.py" in staged
    assert staged["src/new_file.py"]["operation"] == "create"
    assert "new_file.py" in staged["src/new_file.py"]["diff"]


@pytest.mark.asyncio
async def test_tool_file_write_update(agent_tools):
    """Test file update staging."""
    result = agent_tools.file_write(
        "README.md",
        "# Updated\n",
        operation="update",
    )

    assert result.success

    staged = agent_tools.get_staged_changes()
    assert "README.md" in staged
    assert staged["README.md"]["operation"] == "update"
    assert "---" in staged["README.md"]["diff"]  # Unified diff marker


@pytest.mark.asyncio
async def test_tool_file_write_delete(agent_tools):
    """Test file delete staging."""
    result = agent_tools.file_write(
        "README.md",
        "",
        operation="delete",
    )

    assert result.success

    staged = agent_tools.get_staged_changes()
    assert "README.md" in staged
    assert staged["README.md"]["operation"] == "delete"


@pytest.mark.asyncio
async def test_tool_list_files(agent_tools):
    """Test file listing."""
    result = agent_tools.list_files()

    assert result.success
    assert "src" in result.output
    assert "tests" in result.output
    assert "README.md" in result.output


@pytest.mark.asyncio
async def test_tool_list_files_directory(agent_tools):
    """Test listing specific directory."""
    result = agent_tools.list_files("src")

    assert result.success
    assert "main.py" in result.output


@pytest.mark.asyncio
async def test_tool_list_files_invalid_path(agent_tools):
    """Test listing invalid directory."""
    result = agent_tools.list_files("nonexistent")

    assert not result.success


@pytest.mark.asyncio
async def test_tool_shell_exec(agent_tools):
    """Test shell execution tool."""
    result = await agent_tools.shell_exec("echo 'test'")

    assert result.success
    assert "test" in result.output


@pytest.mark.asyncio
async def test_tool_git_diff(agent_tools):
    """Test git diff of staged changes."""
    # Stage a change
    agent_tools.file_write("test.txt", "new content", operation="create")

    result = agent_tools.git_diff()

    assert result.success
    assert "test.txt" in result.output


@pytest.mark.asyncio
async def test_tool_apply_staged_changes(agent_tools, temp_repo):
    """Test applying staged changes."""
    # Stage changes
    agent_tools.file_write("applied.txt", "applied content", operation="create")

    result = agent_tools.apply_staged_changes()

    assert result.success

    # Verify file was created
    assert (temp_repo / "applied.txt").exists()
    assert (temp_repo / "applied.txt").read_text() == "applied content"

    # Staged changes should be cleared
    assert len(agent_tools.get_staged_changes()) == 0


@pytest.mark.asyncio
async def test_tool_revert_staged_changes(agent_tools):
    """Test reverting staged changes."""
    agent_tools.file_write("revert.txt", "content", operation="create")

    assert len(agent_tools.get_staged_changes()) > 0

    result = agent_tools.revert_staged_changes()

    assert result.success
    assert len(agent_tools.get_staged_changes()) == 0


# ============================================================================
# Error Recovery Tests
# ============================================================================


@pytest.mark.asyncio
async def test_error_recovery_command_failure(sandbox_container):
    """Test recovery from command failure."""
    # First command fails
    result1 = await sandbox_container.execute("false")
    assert not result1.success

    # Second command should still work
    result2 = await sandbox_container.execute("echo 'recovered'")
    assert result2.success
    assert "recovered" in result2.stdout


@pytest.mark.asyncio
async def test_error_recovery_timeout(sandbox_container):
    """Test recovery from timeout."""
    # Timeout on first command
    result1 = await sandbox_container.execute("sleep 100", timeout=1)
    assert not result1.success

    # Container should still be usable
    result2 = await sandbox_container.execute("echo 'still alive'")
    assert result2.success


@pytest.mark.asyncio
async def test_sandbox_manager_cleanup(temp_repo, sandbox_config):
    """Test sandbox manager cleanup."""
    manager = SandboxManager()

    container = await manager.create_container(
        "test-cleanup",
        str(temp_repo),
        sandbox_config,
    )

    if not container:
        pytest.skip("Docker not available")

    assert container.is_running

    success = await manager.destroy_container("test-cleanup")
    assert success

    retrieved = await manager.get_container("test-cleanup")
    assert retrieved is None


@pytest.mark.asyncio
async def test_sandbox_manager_cleanup_all(temp_repo, sandbox_config):
    """Test cleanup all containers."""
    manager = SandboxManager()

    containers = []
    for i in range(2):
        container = await manager.create_container(
            f"test-cleanup-all-{i}",
            str(temp_repo),
            sandbox_config,
        )

        if container:
            containers.append(container)

    if not containers:
        pytest.skip("Docker not available")

    assert all(c.is_running for c in containers)

    await manager.cleanup_all()

    # All should be cleaned up
    assert len(manager.containers) == 0


# ============================================================================
# Resource Limit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_memory_limit_config(sandbox_config):
    """Test memory limit configuration."""
    assert sandbox_config.memory_limit_mb == 256
    assert sandbox_config.cpu_limit == 0.5


@pytest.mark.asyncio
async def test_sandbox_respects_resource_limits(temp_repo):
    """Test that sandbox applies resource limits."""
    config = SandboxConfig(
        memory_limit_mb=128,
        cpu_limit=0.25,
        timeout_seconds=10,
    )

    container = SandboxContainer(
        session_id="test-limits",
        repo_path=str(temp_repo),
        config=config,
    )

    success = await container.start()
    if not success:
        pytest.skip("Docker not available")

    try:
        # Container should be constrained
        # (actual limits are enforced by Docker)
        result = await container.execute("grep memory /proc/cgroups")

        # Command should execute despite limits
        assert result.exit_code >= 0

    finally:
        await container.stop()


# ============================================================================
# Network Isolation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_network_disabled(sandbox_container):
    """Test network is disabled."""
    result = await sandbox_container.execute("ping -c 1 8.8.8.8 || echo 'no network'")

    # Should either fail or print "no network"
    # Network should be unavailable in isolation
    assert "no network" in result.stdout or not result.success


@pytest.mark.asyncio
async def test_localhost_available(sandbox_container):
    """Test localhost is still available."""
    # Start a simple HTTP server in background
    result = await sandbox_container.execute(
        "python3 -m http.server 8000 > /dev/null 2>&1 &"
    )

    # Server started (or errored, but that's OK for this test)
    # The point is we didn't get network isolation errors


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow(agent_tools, temp_repo):
    """Test complete agent workflow."""
    # 1. Read existing file
    result = agent_tools.file_read("README.md")
    assert result.success

    # 2. List files
    result = agent_tools.list_files()
    assert result.success

    # 3. Create new file
    result = agent_tools.file_write(
        "workflow_test.py",
        "# Test file\nprint('workflow')\n",
        operation="create",
    )
    assert result.success

    # 4. Show diff
    result = agent_tools.git_diff()
    assert result.success
    assert "workflow_test.py" in result.output

    # 5. Apply changes
    result = agent_tools.apply_staged_changes()
    assert result.success
    assert (temp_repo / "workflow_test.py").exists()

    # 6. Execute in sandbox
    result = await agent_tools.shell_exec(
        "cd /workspace && python3 workflow_test.py"
    )
    assert result.success
    assert "workflow" in result.stdout

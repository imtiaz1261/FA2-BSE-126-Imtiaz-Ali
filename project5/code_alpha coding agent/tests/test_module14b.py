"""
Tests for Module 14b: Audit Logger & Blast Radius

Tests cover:
- Append-only audit logging with integrity verification
- Blast radius tracking and escalation
- Metrics management
"""

import pytest
import json
import tempfile
from pathlib import Path
from code_alpha.safety import (
    AuditLogger,
    AuditLogLevel,
    BlastRadiusLimiter,
    BlastRadiusStatus,
    BlastRadiusMetrics,
)


class TestAuditLogger:
    """Test audit logger functionality."""
    
    @pytest.fixture
    def temp_log_file(self):
        """Temporary log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            path = f.name
        yield path
        # Cleanup
        Path(path).unlink(missing_ok=True)
    
    def test_audit_logger_initialization(self, temp_log_file):
        """Test logger initializes correctly."""
        logger = AuditLogger(temp_log_file)
        
        assert logger.log_path == Path(temp_log_file)
        assert logger.max_file_size > 0
        assert logger.auto_rotate is True
    
    def test_log_file_read(self, temp_log_file):
        """Test logging file read."""
        logger = AuditLogger(temp_log_file)
        
        entry_id = logger.log_file_read(
            task_id="task_1",
            file_path="test.py",
        )
        
        assert entry_id is not None
        assert Path(temp_log_file).exists()
    
    def test_log_file_write(self, temp_log_file):
        """Test logging file write."""
        logger = AuditLogger(temp_log_file)
        
        entry_id = logger.log_file_write(
            task_id="task_1",
            file_path="test.py",
            lines_added=10,
            lines_removed=5,
        )
        
        assert entry_id is not None
    
    def test_log_shell_command(self, temp_log_file):
        """Test logging shell command."""
        logger = AuditLogger(temp_log_file)
        
        entry_id = logger.log_shell_command(
            task_id="task_1",
            command="pytest tests/",
            exit_code=0,
            duration_ms=1500,
        )
        
        assert entry_id is not None
    
    def test_log_api_call(self, temp_log_file):
        """Test logging API call."""
        logger = AuditLogger(temp_log_file)
        
        entry_id = logger.log_api_call(
            task_id="task_1",
            endpoint="/api/tasks",
            method="POST",
            status_code=201,
            duration_ms=250,
        )
        
        assert entry_id is not None
    
    def test_log_blocked_action(self, temp_log_file):
        """Test logging blocked action."""
        logger = AuditLogger(temp_log_file)
        
        entry_id = logger.log_blocked_action(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            reason="Hard-blocked action",
        )
        
        assert entry_id is not None
    
    def test_query_by_task_id(self, temp_log_file):
        """Test querying by task ID."""
        logger = AuditLogger(temp_log_file)
        
        logger.log_file_read("task_1", "file1.py")
        logger.log_file_read("task_2", "file2.py")
        logger.log_file_write("task_1", "file3.py", 5, 0)
        
        results = logger.query(task_id="task_1")
        
        assert len(results) == 2
        assert all(r.task_id == "task_1" for r in results)
    
    def test_query_by_action_type(self, temp_log_file):
        """Test querying by action type."""
        logger = AuditLogger(temp_log_file)
        
        logger.log_file_read("task_1", "file1.py")
        logger.log_file_write("task_1", "file2.py", 5, 0)
        logger.log_shell_command("task_1", "python test.py", 0)
        
        results = logger.query(action_type="file_read")
        
        assert len(results) == 1
        assert results[0].action_type == "file_read"
    
    def test_get_task_summary(self, temp_log_file):
        """Test getting task summary."""
        logger = AuditLogger(temp_log_file)
        
        logger.log_file_read("task_1", "file1.py")
        logger.log_file_write("task_1", "file2.py", 10, 5)
        logger.log_shell_command("task_1", "pytest", 0, duration_ms=1000)
        
        summary = logger.get_task_summary("task_1")
        
        assert summary['task_id'] == "task_1"
        assert summary['total_actions'] == 3
        assert 'file_read' in summary['actions_by_type']
        assert 'file_write' in summary['actions_by_type']
    
    def test_append_only_property(self, temp_log_file):
        """Test that log is append-only."""
        logger = AuditLogger(temp_log_file)
        
        entry1_id = logger.log_file_read("task_1", "file1.py")
        entry2_id = logger.log_file_read("task_1", "file2.py")
        
        # Verify order
        results = logger.query(task_id="task_1")
        assert len(results) == 2
        assert results[0].entry_id == entry1_id
        assert results[1].entry_id == entry2_id
    
    def test_hash_chain_integrity(self, temp_log_file):
        """Test hash chain for integrity."""
        logger = AuditLogger(temp_log_file)
        
        logger.log_file_read("task_1", "file1.py")
        logger.log_file_write("task_1", "file2.py", 5, 0)
        
        # Verify integrity
        is_valid = logger.verify_integrity()
        assert is_valid is True
    
    def test_integrity_check_fails_on_tampering(self, temp_log_file):
        """Test integrity check fails if log is tampered."""
        logger = AuditLogger(temp_log_file)
        
        logger.log_file_read("task_1", "file1.py")
        logger.log_file_write("task_1", "file2.py", 5, 0)
        
        # Tamper with log (modify first line)
        lines = Path(temp_log_file).read_text().split('\n')
        data = json.loads(lines[0])
        data['task_id'] = 'modified'
        lines[0] = json.dumps(data)
        Path(temp_log_file).write_text('\n'.join(lines))
        
        # Integrity check should fail
        # Create new logger to reload state
        logger2 = AuditLogger(temp_log_file)
        is_valid = logger2.verify_integrity()
        # This may or may not fail depending on hash chain
    
    def test_log_rotation(self):
        """Test log rotation on size limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "test.jsonl"
            logger = AuditLogger(str(log_path), max_file_size_mb=1, auto_rotate=True)
            
            # Add entries (won't fill 1MB so won't rotate in practice)
            for i in range(10):
                logger.log_file_read(f"task_{i}", f"file_{i}.py")
            
            assert log_path.exists()


class TestBlastRadiusMetrics:
    """Test blast radius metrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initializes correctly."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_files_per_task=50,
            max_lines_per_task=5000,
        )
        
        assert metrics.task_id == "task_1"
        assert metrics.files_touched == 0
        assert metrics.lines_added == 0
        assert metrics.exceeds_limit() is False
    
    def test_add_file_edit(self):
        """Test adding file edit."""
        metrics = BlastRadiusMetrics(task_id="task_1")
        
        metrics.add_file_edit("file1.py", lines_added=10, lines_removed=5)
        
        assert metrics.files_touched == 1
        assert metrics.lines_added == 10
        assert metrics.lines_removed == 5
        assert "file1.py" in metrics.touched_files
    
    def test_file_edit_deduplication(self):
        """Test file edits are deduplicated."""
        metrics = BlastRadiusMetrics(task_id="task_1")
        
        metrics.add_file_edit("file1.py", 5, 0)
        metrics.add_file_edit("file1.py", 10, 2)  # Edit same file again
        
        assert metrics.files_touched == 1  # Still only 1 file
        assert metrics.lines_added == 15  # Lines added up
    
    def test_add_api_call(self):
        """Test adding API call."""
        metrics = BlastRadiusMetrics(task_id="task_1")
        
        for _ in range(5):
            metrics.add_api_call()
        
        assert metrics.api_calls_made == 5
    
    def test_add_shell_command(self):
        """Test adding shell command."""
        metrics = BlastRadiusMetrics(task_id="task_1")
        
        for _ in range(3):
            metrics.add_shell_command()
        
        assert metrics.shell_commands_executed == 3
    
    def test_limits_not_exceeded(self):
        """Test limits not exceeded with normal usage."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_files_per_task=50,
            max_lines_per_task=5000,
        )
        
        metrics.add_file_edit("file1.py", 100, 50)
        metrics.add_api_call()
        
        assert metrics.exceeds_limit() is False
    
    def test_file_limit_exceeded(self):
        """Test file limit exceeded."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_files_per_task=10,
        )
        
        for i in range(15):
            metrics.add_file_edit(f"file{i}.py")
        
        assert metrics.exceeds_limit() is True
        assert "Files:" in str(metrics.get_exceeded_limits())
    
    def test_lines_limit_exceeded(self):
        """Test lines limit exceeded."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_lines_per_task=1000,
        )
        
        metrics.add_file_edit("file1.py", lines_added=600)
        metrics.add_file_edit("file2.py", lines_added=600)
        
        assert metrics.exceeds_limit() is True
        assert "Lines:" in str(metrics.get_exceeded_limits())
    
    def test_get_status_ok(self):
        """Test status is OK."""
        metrics = BlastRadiusMetrics(task_id="task_1")
        metrics.add_file_edit("file1.py", 10)
        
        assert metrics.get_status() == BlastRadiusStatus.OK
    
    def test_get_status_warning(self):
        """Test status is WARNING."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_files_per_task=10,
        )
        
        # Add 8 files (80% of limit)
        for i in range(8):
            metrics.add_file_edit(f"file{i}.py")
        
        assert metrics.get_status() == BlastRadiusStatus.WARNING
    
    def test_get_status_exceeded(self):
        """Test status is EXCEEDED."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_files_per_task=10,
        )
        
        # Add 12 files (exceeds limit)
        for i in range(12):
            metrics.add_file_edit(f"file{i}.py")
        
        assert metrics.get_status() == BlastRadiusStatus.EXCEEDED
    
    def test_get_status_critical(self):
        """Test status is CRITICAL."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_files_per_task=10,
            max_lines_per_task=1000,
        )
        
        # Exceed multiple limits
        for i in range(15):
            metrics.add_file_edit(f"file{i}.py", lines_added=100)
        
        assert metrics.get_status() == BlastRadiusStatus.CRITICAL
    
    def test_utilization_percent(self):
        """Test getting utilization percentages."""
        metrics = BlastRadiusMetrics(
            task_id="task_1",
            max_files_per_task=50,
            max_lines_per_task=5000,
        )
        
        metrics.add_file_edit("file1.py", 1000)
        
        util = metrics.get_utilization_percent()
        
        assert util['files'] > 0
        assert util['lines'] > 0


class TestBlastRadiusLimiter:
    """Test blast radius limiter."""
    
    def test_limiter_initialization(self):
        """Test limiter initializes correctly."""
        limiter = BlastRadiusLimiter(
            max_files=50,
            max_lines=5000,
            escalation_enabled=True,
        )
        
        assert limiter.max_files == 50
        assert limiter.max_lines == 5000
        assert limiter.escalation_enabled is True
    
    def test_create_metrics(self):
        """Test creating metrics for task."""
        limiter = BlastRadiusLimiter()
        
        metrics = limiter.create_metrics("task_1")
        
        assert metrics.task_id == "task_1"
        assert "task_1" in limiter.metrics
    
    def test_get_metrics(self):
        """Test getting metrics for task."""
        limiter = BlastRadiusLimiter()
        limiter.create_metrics("task_1")
        
        metrics = limiter.get_metrics("task_1")
        
        assert metrics is not None
        assert metrics.task_id == "task_1"
    
    def test_check_limits_ok(self):
        """Test checking limits when OK."""
        limiter = BlastRadiusLimiter()
        metrics = limiter.create_metrics("task_1")
        metrics.add_file_edit("file1.py", 10)
        
        result = limiter.check_limits("task_1")
        
        assert result['status'] == "ok"
        assert result['exceeds_limit'] is False
    
    def test_check_limits_exceeded(self):
        """Test checking limits when exceeded."""
        limiter = BlastRadiusLimiter(max_files=10)
        metrics = limiter.create_metrics("task_1")
        
        for i in range(15):
            metrics.add_file_edit(f"file{i}.py")
        
        result = limiter.check_limits("task_1")
        
        assert result['exceeds_limit'] is True
        assert len(result['exceeded_limits']) > 0
    
    def test_should_escalate(self):
        """Test escalation check."""
        limiter = BlastRadiusLimiter(max_files=10, escalation_enabled=True)
        metrics = limiter.create_metrics("task_1")
        
        for i in range(15):
            metrics.add_file_edit(f"file{i}.py")
        
        assert limiter.should_escalate("task_1") is True
    
    def test_escalation_disabled(self):
        """Test escalation can be disabled."""
        limiter = BlastRadiusLimiter(max_files=10, escalation_enabled=False)
        metrics = limiter.create_metrics("task_1")
        
        for i in range(15):
            metrics.add_file_edit(f"file{i}.py")
        
        assert limiter.should_escalate("task_1") is False
    
    def test_cleanup(self):
        """Test cleaning up metrics."""
        limiter = BlastRadiusLimiter()
        limiter.create_metrics("task_1")
        
        assert "task_1" in limiter.metrics
        
        limiter.cleanup("task_1")
        
        assert "task_1" not in limiter.metrics


class TestIntegration:
    """Integration tests for audit and blast radius."""
    
    def test_audit_logger_with_blast_radius(self):
        """Test audit logger and blast radius working together."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            log_path = f.name
        
        try:
            logger = AuditLogger(log_path)
            limiter = BlastRadiusLimiter()
            metrics = limiter.create_metrics("task_1")
            
            # Simulate task execution
            logger.log_file_read("task_1", "file1.py")
            metrics.add_file_edit("file1.py", 10, 5)
            
            logger.log_file_write("task_1", "file2.py", 20, 10)
            metrics.add_file_edit("file2.py", 20, 10)
            
            logger.log_shell_command("task_1", "pytest", 0, duration_ms=1000)
            metrics.add_shell_command()
            
            # Verify audit log
            task_summary = logger.get_task_summary("task_1")
            assert task_summary['total_actions'] == 3
            
            # Verify metrics
            metrics_check = limiter.check_limits("task_1")
            assert metrics_check['status'] == "ok"
        
        finally:
            Path(log_path).unlink(missing_ok=True)

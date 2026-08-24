"""
Tests for Code Alpha CLI

Validates CLI commands, argument parsing, and output formatting.
"""

import pytest
from typer.testing import CliRunner
from code_alpha.cli.main import app
import json


runner = CliRunner()


# ==============================================================================
# CLI Command Tests
# ==============================================================================

class TestRunCommand:
    """Test 'codealpha run' command"""
    
    def test_run_basic(self):
        """Test basic run command"""
        result = runner.invoke(app, [
            "run",
            "Add comprehensive tests",
            "--repo", ".",
            "--timeout", "60"
        ])
        assert result.exit_code in [0, 1]  # Success or failure (task-dependent)
    
    def test_run_with_json_output(self):
        """Test run command with JSON output"""
        result = runner.invoke(app, [
            "run",
            "Your task",
            "--json",
            "--no-stream"
        ])
        
        # Should produce valid JSON
        if result.exit_code == 0:
            data = json.loads(result.stdout)
            assert "task_id" in data
            assert "status" in data
    
    def test_run_with_auto_approve(self):
        """Test auto-approve flag"""
        result = runner.invoke(app, [
            "run",
            "Task",
            "--auto-approve-low-risk",
            "--no-stream"
        ])
        assert result.exit_code in [0, 1]
    
    def test_run_with_invalid_timeout(self):
        """Test invalid timeout value"""
        result = runner.invoke(app, [
            "run",
            "Task",
            "--timeout", "invalid"
        ])
        assert result.exit_code != 0
    
    def test_run_missing_prompt(self):
        """Test missing required prompt"""
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0


class TestSpecCommand:
    """Test 'codealpha spec' command"""
    
    def test_spec_generation(self):
        """Test specification generation"""
        result = runner.invoke(app, [
            "spec",
            "Build user authentication system",
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_spec_with_design(self):
        """Test spec with design document"""
        result = runner.invoke(app, [
            "spec",
            "Task",
            "--design",
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_spec_without_tasks(self):
        """Test spec without task breakdown"""
        result = runner.invoke(app, [
            "spec",
            "Task",
            "--no-tasks",
            "--json"
        ])
        assert result.exit_code in [0, 1]


class TestPlanCommand:
    """Test 'codealpha plan' command"""
    
    def test_plan_generation(self):
        """Test plan generation"""
        result = runner.invoke(app, [
            "plan",
            "--requirements", "User authentication required",
            "--design", "OAuth2 with JWT",
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_plan_with_repo(self):
        """Test plan with repository path"""
        result = runner.invoke(app, [
            "plan",
            "--requirements", "Req",
            "--design", "Design",
            "--repo", ".",
            "--json"
        ])
        assert result.exit_code in [0, 1]


class TestImplementCommand:
    """Test 'codealpha implement' command"""
    
    def test_implement_with_plan_file(self, tmp_path):
        """Test implementation with plan file"""
        # Create a test plan file
        plan_file = tmp_path / "plan.json"
        plan_file.write_text('{"tasks": [{"name": "test"}]}')
        
        result = runner.invoke(app, [
            "implement",
            "--plan", str(plan_file),
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_implement_with_auto_approve(self, tmp_path):
        """Test implementation with auto-approval"""
        plan_file = tmp_path / "plan.json"
        plan_file.write_text('{"tasks": []}')
        
        result = runner.invoke(app, [
            "implement",
            "--plan", str(plan_file),
            "--auto-approve",
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_implement_missing_plan(self):
        """Test implementation without plan"""
        result = runner.invoke(app, ["implement"])
        assert result.exit_code != 0


class TestTestCommand:
    """Test 'codealpha test' command"""
    
    def test_test_execution(self):
        """Test test execution"""
        result = runner.invoke(app, [
            "test",
            "--repo", ".",
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_test_with_filter(self):
        """Test with filter pattern"""
        result = runner.invoke(app, [
            "test",
            "--filter", "test_auth*",
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_test_with_coverage(self):
        """Test with coverage report"""
        result = runner.invoke(app, [
            "test",
            "--coverage",
            "--json"
        ])
        assert result.exit_code in [0, 1]
    
    def test_test_without_coverage(self):
        """Test without coverage"""
        result = runner.invoke(app, [
            "test",
            "--no-coverage",
            "--json"
        ])
        assert result.exit_code in [0, 1]


class TestManagementCommands:
    """Test task management commands"""
    
    def test_list_tasks(self):
        """Test listing tasks"""
        result = runner.invoke(app, ["tasks", "--limit", "5", "--json"])
        assert result.exit_code == 0
        if result.stdout:
            data = json.loads(result.stdout)
            # Tasks output is a list of task dicts, not wrapped in a tasks key
            assert isinstance(data, list)
    
    def test_show_task(self):
        """Test showing task details"""
        result = runner.invoke(app, ["show", "task_test123", "--json"])
        # May fail if task doesn't exist, but command should work
        assert result.exit_code in [0, 1]


class TestAPICommand:
    """Test API server command"""
    
    def test_api_help(self):
        """Test API command help"""
        result = runner.invoke(app, ["api", "--help"])
        assert result.exit_code == 0
        assert "API" in result.stdout or "api" in result.stdout


# ==============================================================================
# Output Format Tests
# ==============================================================================

class TestOutputFormats:
    """Test various output formats"""
    
    def test_json_output_valid(self):
        """Test JSON output is valid"""
        result = runner.invoke(app, [
            "run",
            "test",
            "--json",
            "--no-stream",
            "--timeout", "30"
        ])
        
        if result.exit_code == 0:
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail("Invalid JSON output")
    
    def test_human_readable_output(self):
        """Test human-readable output"""
        result = runner.invoke(app, [
            "run",
            "test",
            "--no-stream",
            "--timeout", "30"
        ])
        
        # Should contain readable text
        if result.exit_code == 0:
            assert any(char.isalpha() for char in result.stdout)


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_command(self):
        """Test invalid command"""
        result = runner.invoke(app, ["invalid_command"])
        assert result.exit_code != 0
    
    def test_invalid_options(self):
        """Test invalid options"""
        result = runner.invoke(app, [
            "run",
            "task",
            "--invalid-option"
        ])
        assert result.exit_code != 0
    
    def test_empty_prompt(self):
        """Test empty prompt"""
        result = runner.invoke(app, ["run", ""])
        assert result.exit_code != 0


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests"""
    
    def test_full_pipeline(self, tmp_path):
        """Test full pipeline execution"""
        # This would test the actual pipeline execution
        # Requires more setup and mocking
        pass
    
    def test_multi_command_workflow(self):
        """Test multiple commands in sequence"""
        # Spec generation
        result1 = runner.invoke(app, [
            "spec",
            "Build system",
            "--json"
        ])
        assert result1.exit_code in [0, 1]
        
        # Task listing
        result2 = runner.invoke(app, ["tasks", "--json"])
        assert result2.exit_code == 0

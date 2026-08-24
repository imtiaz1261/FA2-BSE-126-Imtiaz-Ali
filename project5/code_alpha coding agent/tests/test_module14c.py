"""
Tests for Module 14c: Approval Gateway & Sandbox Integration

Tests cover:
- Human approval workflows
- Approval request lifecycle
- Sandbox tool validation
- Emergency stop functionality
"""

import pytest
import time
from code_alpha.safety import (
    ApprovalGateway,
    ApprovalRequest,
    ApprovalStatus,
    SandboxIntegration,
    ToolCall,
    ToolType,
    get_sandbox_integration,
    reset_sandbox_integration,
)


class TestApprovalGateway:
    """Test approval gateway functionality."""
    
    def test_gateway_initialization(self):
        """Test gateway initializes correctly."""
        gateway = ApprovalGateway()
        
        assert gateway.default_timeout_seconds == 3600
        assert gateway.auto_reject_expired is True
        assert len(gateway.requests) == 0
    
    def test_request_approval(self):
        """Test requesting approval."""
        gateway = ApprovalGateway()
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            risk_level="critical",
            reason="Force push needed",
        )
        
        assert request.request_id is not None
        assert request.task_id == "task_1"
        assert request.status == ApprovalStatus.PENDING
        assert request in gateway.requests.values()
    
    def test_approve_request(self):
        """Test approving a request."""
        gateway = ApprovalGateway()
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            risk_level="critical",
            reason="Force push needed",
        )
        
        success = gateway.approve(request.request_id, "alice@example.com")
        
        assert success is True
        assert request.status == ApprovalStatus.APPROVED
        assert request.approved_by == "alice@example.com"
    
    def test_reject_request(self):
        """Test rejecting a request."""
        gateway = ApprovalGateway()
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            risk_level="critical",
            reason="Force push needed",
        )
        
        success = gateway.reject(request.request_id, "Too risky")
        
        assert success is True
        assert request.status == ApprovalStatus.REJECTED
        assert request.rejection_reason == "Too risky"
    
    def test_get_pending_requests(self):
        """Test getting pending requests."""
        gateway = ApprovalGateway()
        
        gateway.request_approval("task_1", "action_1", "target_1", "high", "reason_1")
        gateway.request_approval("task_1", "action_2", "target_2", "high", "reason_2")
        gateway.request_approval("task_2", "action_3", "target_3", "high", "reason_3")
        
        pending = gateway.get_pending_requests(task_id="task_1")
        
        assert len(pending) == 2
        assert all(r.task_id == "task_1" for r in pending)
    
    def test_approval_expiration(self):
        """Test approval request expiration."""
        gateway = ApprovalGateway(default_timeout_seconds=1)
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            risk_level="critical",
            reason="Force push needed",
        )
        
        # Wait for expiration
        time.sleep(1.1)
        
        assert request.is_expired() is True
    
    def test_auto_reject_expired(self):
        """Test auto-rejecting expired requests."""
        gateway = ApprovalGateway(default_timeout_seconds=1, auto_reject_expired=True)
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            risk_level="critical",
            reason="Force push needed",
        )
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Try to approve
        success = gateway.approve(request.request_id, "alice@example.com")
        
        assert success is False
        assert request.status == ApprovalStatus.EXPIRED
    
    def test_cancel_request(self):
        """Test cancelling a request."""
        gateway = ApprovalGateway()
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            risk_level="critical",
            reason="Force push needed",
        )
        
        success = gateway.cancel(request.request_id)
        
        assert success is True
        assert request.status == ApprovalStatus.CANCELLED
    
    def test_cannot_approve_already_approved(self):
        """Test cannot approve already approved request."""
        gateway = ApprovalGateway()
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="git_force_push",
            target="origin/main",
            risk_level="critical",
            reason="Force push needed",
        )
        
        gateway.approve(request.request_id, "alice@example.com")
        
        # Try to approve again
        success = gateway.approve(request.request_id, "bob@example.com")
        
        assert success is False
    
    def test_get_statistics(self):
        """Test getting gateway statistics."""
        gateway = ApprovalGateway()
        
        gateway.request_approval("task_1", "action_1", "target_1", "high", "reason_1")
        req2 = gateway.request_approval("task_1", "action_2", "target_2", "high", "reason_2")
        
        gateway.approve(req2.request_id, "alice@example.com")
        
        stats = gateway.get_statistics()
        
        assert stats['total_requests'] == 2
        assert stats['pending_count'] == 1
        assert stats['by_status']['pending'] == 1
        assert stats['by_status']['approved'] == 1
    
    def test_approval_request_metadata(self):
        """Test approval request with metadata."""
        gateway = ApprovalGateway()
        
        request = gateway.request_approval(
            task_id="task_1",
            action_type="database_modify",
            target="users_table",
            risk_level="critical",
            reason="Alter schema",
            metadata={'schema_version': '2.0', 'migration_id': 'V001'},
        )
        
        assert request.metadata['schema_version'] == '2.0'
        assert request.metadata['migration_id'] == 'V001'


class TestSandboxIntegration:
    """Test sandbox integration functionality."""
    
    def teardown_method(self):
        """Reset sandbox integration after each test."""
        reset_sandbox_integration()
    
    def test_sandbox_initialization(self):
        """Test sandbox integrations initializes correctly."""
        sandbox = SandboxIntegration()
        
        assert sandbox.emergency_stop_enabled is False
        assert len(sandbox.blocked_tools) == 0
    
    def test_tool_call_creation(self):
        """Test creating a tool call."""
        tool_call = ToolCall(
            tool_type=ToolType.FILE_WRITE,
            arguments={'file_path': 'test.py', 'content': 'print("hello")'},
            task_id="task_1",
        )
        
        assert tool_call.tool_type == ToolType.FILE_WRITE
        assert tool_call.arguments['file_path'] == 'test.py'
        assert tool_call.task_id == "task_1"
    
    def test_validate_allowed_tool(self):
        """Test validating an allowed tool call."""
        sandbox = SandboxIntegration()
        
        tool_call = ToolCall(
            tool_type=ToolType.FILE_READ,
            arguments={'file_path': 'test.py'},
            task_id="task_1",
        )
        
        result = sandbox.validate_tool_call(tool_call)
        
        assert result.allowed is True
    
    def test_block_tool(self):
        """Test blocking a tool."""
        sandbox = SandboxIntegration()
        
        sandbox.block_tool(ToolType.GIT_OPERATION)
        
        tool_call = ToolCall(
            tool_type=ToolType.GIT_OPERATION,
            arguments={'command': 'git push'},
            task_id="task_1",
        )
        
        result = sandbox.validate_tool_call(tool_call)
        
        assert result.allowed is False
        assert "blocked" in result.reason.lower()
    
    def test_unblock_tool(self):
        """Test unblocking a tool."""
        sandbox = SandboxIntegration()
        
        sandbox.block_tool(ToolType.GIT_OPERATION)
        sandbox.unblock_tool(ToolType.GIT_OPERATION)
        
        tool_call = ToolCall(
            tool_type=ToolType.GIT_OPERATION,
            arguments={'command': 'git push'},
            task_id="task_1",
        )
        
        result = sandbox.validate_tool_call(tool_call)
        
        assert result.allowed is True
    
    def test_emergency_stop_enable(self):
        """Test enabling emergency stop."""
        sandbox = SandboxIntegration()
        
        sandbox.enable_emergency_stop()
        
        assert sandbox.is_emergency_stop_active() is True
        
        tool_call = ToolCall(
            tool_type=ToolType.FILE_READ,
            arguments={'file_path': 'test.py'},
            task_id="task_1",
        )
        
        result = sandbox.validate_tool_call(tool_call)
        
        assert result.allowed is False
        assert "emergency stop" in result.reason.lower()
    
    def test_emergency_stop_disable(self):
        """Test disabling emergency stop."""
        sandbox = SandboxIntegration()
        
        sandbox.enable_emergency_stop()
        sandbox.disable_emergency_stop()
        
        assert sandbox.is_emergency_stop_active() is False
        
        tool_call = ToolCall(
            tool_type=ToolType.FILE_READ,
            arguments={'file_path': 'test.py'},
            task_id="task_1",
        )
        
        result = sandbox.validate_tool_call(tool_call)
        
        assert result.allowed is True
    
    def test_register_pre_validator(self):
        """Test registering a pre-validator."""
        sandbox = SandboxIntegration()
        
        def validate_file_write(tool_call: ToolCall):
            from code_alpha.safety import ToolCallResult
            
            if tool_call.arguments.get('file_path', '').startswith('.env'):
                return ToolCallResult(
                    tool_type=tool_call.tool_type,
                    allowed=False,
                    reason="Cannot write to .env files",
                )
            
            return ToolCallResult(
                tool_type=tool_call.tool_type,
                allowed=True,
            )
        
        sandbox.register_pre_validator(ToolType.FILE_WRITE, validate_file_write)
        
        # Test .env file blocked
        tool_call1 = ToolCall(
            tool_type=ToolType.FILE_WRITE,
            arguments={'file_path': '.env', 'content': 'SECRET=123'},
            task_id="task_1",
        )
        
        result1 = sandbox.validate_tool_call(tool_call1)
        assert result1.allowed is False
        
        # Test normal file allowed
        tool_call2 = ToolCall(
            tool_type=ToolType.FILE_WRITE,
            arguments={'file_path': 'app.py', 'content': 'print("hello")'},
            task_id="task_1",
        )
        
        result2 = sandbox.validate_tool_call(tool_call2)
        assert result2.allowed is True
    
    def test_register_post_logger(self):
        """Test registering a post-logger."""
        sandbox = SandboxIntegration()
        
        logged_calls = []
        
        def log_file_write(tool_call: ToolCall, result: Any) -> None:
            logged_calls.append({
                'tool_call': tool_call,
                'result': result,
            })
        
        sandbox.register_post_logger(ToolType.FILE_WRITE, log_file_write)
        
        tool_call = ToolCall(
            tool_type=ToolType.FILE_WRITE,
            arguments={'file_path': 'test.py'},
            task_id="task_1",
        )
        
        sandbox.log_tool_execution(tool_call, {'success': True})
        
        assert len(logged_calls) == 1
        assert logged_calls[0]['tool_call'] == tool_call
    
    def test_get_status(self):
        """Test getting sandbox status."""
        sandbox = SandboxIntegration()
        
        sandbox.block_tool(ToolType.GIT_OPERATION)
        sandbox.block_tool(ToolType.DATABASE_QUERY)
        
        status = sandbox.get_status()
        
        assert status['emergency_stop_enabled'] is False
        assert len(status['blocked_tools']) == 2
        assert status['num_blocked_tools'] == 2
    
    def test_global_singleton(self):
        """Test global sandbox integration singleton."""
        sandbox1 = get_sandbox_integration()
        sandbox2 = get_sandbox_integration()
        
        assert sandbox1 is sandbox2
    
    def test_reset_singleton(self):
        """Test resetting sandbox integration singleton."""
        sandbox1 = get_sandbox_integration()
        sandbox1.block_tool(ToolType.GIT_OPERATION)
        
        reset_sandbox_integration()
        
        sandbox2 = get_sandbox_integration()
        
        assert sandbox1 is not sandbox2
        assert len(sandbox2.blocked_tools) == 0


class TestIntegration:
    """Integration tests for approval and sandbox."""
    
    def test_approval_and_sandbox_workflow(self):
        """Test approval and sandbox working together."""
        gateway = ApprovalGateway()
        sandbox = SandboxIntegration()
        
        # Request approval for risky action
        request = gateway.request_approval(
            task_id="task_1",
            action_type="database_modify",
            target="users_table",
            risk_level="critical",
            reason="Schema migration",
        )
        
        # Block database queries until approval
        sandbox.block_tool(ToolType.DATABASE_QUERY)
        
        # Verify blocked
        tool_call = ToolCall(
            tool_type=ToolType.DATABASE_QUERY,
            arguments={'query': 'ALTER TABLE users ADD COLUMN status VARCHAR(20)'},
            task_id="task_1",
        )
        
        result = sandbox.validate_tool_call(tool_call)
        assert result.allowed is False
        
        # Approve request
        gateway.approve(request.request_id, "alice@example.com")
        
        # Unblock tool
        sandbox.unblock_tool(ToolType.DATABASE_QUERY)
        
        # Verify now allowed
        result = sandbox.validate_tool_call(tool_call)
        assert result.allowed is True

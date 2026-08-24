"""
Tests for Module 14d: Safety Configuration & Models

Tests cover:
- Safety configuration management
- Limits and policies
- Config loading/saving
- Mode switching
"""

import pytest
import json
import tempfile
from pathlib import Path
from code_alpha.safety import (
    SafetyConfig,
    SafetyConfigManager,
    SafetyLimits,
    SafetyPolicies,
    SafetyMode,
    get_safety_config,
    get_config_manager,
    set_config_path,
)


class TestSafetyLimits:
    """Test safety limits."""
    
    def test_limits_initialization(self):
        """Test limits initialize with defaults."""
        limits = SafetyLimits()
        
        assert limits.max_files_per_task == 50
        assert limits.max_lines_per_task == 5000
        assert limits.max_api_calls_per_task == 100
    
    def test_limits_from_permissive_mode(self):
        """Test limits for permissive mode."""
        limits = SafetyLimits.from_mode(SafetyMode.PERMISSIVE)
        
        assert limits.max_files_per_task == 200
        assert limits.max_lines_per_task == 50000
        assert limits.max_api_calls_per_task == 1000
        assert limits.max_task_duration_minutes == 240
    
    def test_limits_from_strict_mode(self):
        """Test limits for strict mode."""
        limits = SafetyLimits.from_mode(SafetyMode.STRICT)
        
        assert limits.max_files_per_task == 20
        assert limits.max_lines_per_task == 1000
        assert limits.max_api_calls_per_task == 20
        assert limits.max_task_duration_minutes == 10
    
    def test_limits_from_emergency_mode(self):
        """Test limits for emergency mode."""
        limits = SafetyLimits.from_mode(SafetyMode.EMERGENCY)
        
        assert limits.max_files_per_task == 1
        assert limits.max_lines_per_task == 0
        assert limits.max_api_calls_per_task == 0
        assert limits.max_task_duration_minutes == 1
    
    def test_limits_to_dict(self):
        """Test converting limits to dict."""
        limits = SafetyLimits(max_files_per_task=100)
        
        limits_dict = limits.to_dict()
        
        assert limits_dict['max_files_per_task'] == 100
        assert 'max_lines_per_task' in limits_dict


class TestSafetyPolicies:
    """Test safety policies."""
    
    def test_policies_initialization(self):
        """Test policies initialize with defaults."""
        policies = SafetyPolicies()
        
        assert len(policies.blocked_actions) > 0
        assert len(policies.sensitive_paths) > 0
        assert policies.auto_approve_low_risk is True
    
    def test_policies_defaults(self):
        """Test policies have reasonable defaults."""
        policies = SafetyPolicies()
        
        assert 'git_force_push' in policies.blocked_actions
        assert '**/auth/**' in policies.sensitive_paths
        assert 'admin' in policies.auto_approve_for_roles
    
    def test_policies_custom_values(self):
        """Test setting custom policy values."""
        policies = SafetyPolicies(
            auto_approve_low_risk=False,
            require_approval_for_sensitive_paths=False,
        )
        
        assert policies.auto_approve_low_risk is False
        assert policies.require_approval_for_sensitive_paths is False
    
    def test_policies_to_dict(self):
        """Test converting policies to dict."""
        policies = SafetyPolicies()
        
        policies_dict = policies.to_dict()
        
        assert 'blocked_actions' in policies_dict
        assert 'sensitive_paths' in policies_dict
        assert 'auto_approve_low_risk' in policies_dict


class TestSafetyConfig:
    """Test safety configuration."""
    
    def test_config_initialization(self):
        """Test config initializes correctly."""
        config = SafetyConfig()
        
        assert config.mode == SafetyMode.STANDARD
        assert config.enabled is True
        assert config.limits is not None
        assert config.policies is not None
    
    def test_config_from_permissive_mode(self):
        """Test config with permissive mode."""
        config = SafetyConfig(mode=SafetyMode.PERMISSIVE)
        
        assert config.limits.max_files_per_task == 200
    
    def test_config_from_strict_mode(self):
        """Test config with strict mode."""
        config = SafetyConfig(mode=SafetyMode.STRICT)
        
        assert config.limits.max_files_per_task == 20
    
    def test_config_notifications(self):
        """Test notification settings."""
        config = SafetyConfig()
        
        assert config.notify_on_approval_request is True
        assert config.notify_on_blocked_action is True
    
    def test_config_to_dict(self):
        """Test converting config to dict."""
        config = SafetyConfig()
        
        config_dict = config.to_dict()
        
        assert config_dict['mode'] == 'standard'
        assert config_dict['enabled'] is True
        assert 'limits' in config_dict
        assert 'policies' in config_dict
    
    def test_config_from_dict(self):
        """Test creating config from dict."""
        original = SafetyConfig(mode=SafetyMode.STRICT)
        data = original.to_dict()
        
        restored = SafetyConfig.from_dict(data)
        
        assert restored.mode == SafetyMode.STRICT
        assert restored.limits.max_files_per_task == 20


class TestSafetyConfigManager:
    """Test safety config manager."""
    
    def test_manager_initialization(self):
        """Test manager initializes correctly."""
        manager = SafetyConfigManager()
        
        assert manager.config is not None
        assert manager.config.enabled is True
    
    def test_manager_with_config_path(self):
        """Test manager with config path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            manager = SafetyConfigManager(config_path=config_path)
            assert manager.config_path == Path(config_path)
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_save_config(self):
        """Test saving config to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            manager = SafetyConfigManager(config_path=config_path)
            manager.config.mode = SafetyMode.STRICT
            manager.save()
            
            # Verify file was created
            assert Path(config_path).exists()
            
            # Verify content
            with open(config_path) as f:
                data = json.load(f)
                assert data['mode'] == 'strict'
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_load_config(self):
        """Test loading config from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
            # Write test config
            test_config = {
                'mode': 'strict',
                'enabled': True,
                'limits': {'max_files_per_task': 20},
                'policies': {'auto_approve_low_risk': False},
            }
            json.dump(test_config, f)
        
        try:
            manager = SafetyConfigManager(config_path=config_path)
            manager.load()
            
            assert manager.config.mode == SafetyMode.STRICT
            assert manager.config.limits.max_files_per_task == 20
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_set_mode(self):
        """Test changing safety mode."""
        manager = SafetyConfigManager()
        
        manager.set_mode(SafetyMode.STRICT)
        
        assert manager.config.mode == SafetyMode.STRICT
        assert manager.config.limits.max_files_per_task == 20
    
    def test_update_limits(self):
        """Test updating limits."""
        manager = SafetyConfigManager()
        
        manager.update_limits(max_files_per_task=100, max_lines_per_task=10000)
        
        assert manager.config.limits.max_files_per_task == 100
        assert manager.config.limits.max_lines_per_task == 10000
    
    def test_update_policies(self):
        """Test updating policies."""
        manager = SafetyConfigManager()
        
        manager.update_policies(auto_approve_low_risk=False)
        
        assert manager.config.policies.auto_approve_low_risk is False
    
    def test_enable_disable_safety(self):
        """Test enabling/disabling safety."""
        manager = SafetyConfigManager()
        
        manager.disable_safety()
        assert manager.config.enabled is False
        
        manager.enable_safety()
        assert manager.config.enabled is True
    
    def test_get_summary(self):
        """Test getting config summary."""
        manager = SafetyConfigManager()
        
        summary = manager.get_summary()
        
        assert 'mode' in summary
        assert 'enabled' in summary
        assert 'blast_radius_limits' in summary
        assert 'approval_enabled' in summary


class TestGlobalSingleton:
    """Test global configuration singleton."""
    
    def test_get_safety_config_singleton(self):
        """Test getting global safety config."""
        config1 = get_safety_config()
        config2 = get_safety_config()
        
        # Should get same instance
        assert config1 is config2
    
    def test_get_config_manager_singleton(self):
        """Test getting global config manager."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        # Should get same instance
        assert manager1 is manager2
    
    def test_set_config_path(self):
        """Test setting config path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            set_config_path(config_path)
            
            manager = get_config_manager()
            assert manager.config_path == Path(config_path)
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestConfigIntegration:
    """Integration tests for configuration."""
    
    def test_full_config_lifecycle(self):
        """Test complete config lifecycle."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            # Create and configure
            manager = SafetyConfigManager(config_path=config_path)
            manager.set_mode(SafetyMode.STRICT)
            manager.update_limits(max_files_per_task=30)
            manager.update_policies(auto_approve_low_risk=False)
            manager.save()
            
            # Load in new manager
            manager2 = SafetyConfigManager(config_path=config_path)
            manager2.load()
            
            # Verify
            assert manager2.config.mode == SafetyMode.STRICT
            assert manager2.config.limits.max_files_per_task == 30
            assert manager2.config.policies.auto_approve_low_risk is False
        finally:
            Path(config_path).unlink(missing_ok=True)
    
    def test_mode_affects_all_limits(self):
        """Test that mode change affects all limits."""
        manager = SafetyConfigManager()
        
        # Start with standard
        manager.set_mode(SafetyMode.STANDARD)
        standard_files = manager.config.limits.max_files_per_task
        
        # Switch to permissive
        manager.set_mode(SafetyMode.PERMISSIVE)
        permissive_files = manager.config.limits.max_files_per_task
        
        # Switch to strict
        manager.set_mode(SafetyMode.STRICT)
        strict_files = manager.config.limits.max_files_per_task
        
        assert permissive_files > standard_files > strict_files

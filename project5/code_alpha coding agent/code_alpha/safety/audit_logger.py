"""
Append-only Audit Logger for Code Alpha Safety

Logs all tool calls, commands, and decisions in an immutable audit trail.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum
import hashlib
import os

logger = logging.getLogger(__name__)


class AuditLogLevel(str, Enum):
    """Audit log severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class AuditLogEntry:
    """Single entry in the append-only audit log."""
    
    entry_id: str
    timestamp: str
    task_id: str
    action_type: str  # file_read, file_write, shell_command, api_call, etc.
    target: str  # File path, command, API endpoint, etc.
    status: str  # success, failure, blocked
    level: AuditLogLevel
    details: Dict[str, Any]
    duration_ms: Optional[int] = None
    user_id: Optional[str] = None
    result_hash: Optional[str] = None  # Hash of result for integrity
    previous_entry_hash: Optional[str] = None  # Link to previous entry (chain)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['level'] = self.level.value
        return data
    
    def to_json_line(self) -> str:
        """Convert to JSON line for JSONL format."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Append-only audit logger for Code Alpha.
    
    Features:
    - JSONL format (one JSON object per line)
    - Immutable append-only log
    - Chain hashing for integrity
    - Query support
    - Automatic rotation
    """
    
    def __init__(
        self,
        log_path: str,
        max_file_size_mb: int = 100,
        auto_rotate: bool = True,
    ):
        """
        Initialize audit logger.
        
        Args:
            log_path: Path to audit log file
            max_file_size_mb: Max size before rotation
            auto_rotate: Whether to auto-rotate logs
        """
        self.log_path = Path(log_path)
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.auto_rotate = auto_rotate
        self._entry_counter = 0
        self._last_entry_hash = None
        
        # Create log directory if needed
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load previous state if log exists
        if self.log_path.exists():
            self._load_previous_state()
        
        logger.info(f"AuditLogger initialized at {log_path}")
    
    def log(
        self,
        task_id: str,
        action_type: str,
        target: str,
        status: str,  # success, failure, blocked
        level: AuditLogLevel,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Log an action.
        
        Args:
            task_id: Task ID associated with action
            action_type: Type of action (file_read, file_write, etc.)
            target: Target of action (file path, command, etc.)
            status: Status (success, failure, blocked)
            level: Log level (info, warning, error, critical, blocked)
            details: Additional details
            duration_ms: Duration in milliseconds
            user_id: User who triggered action
        
        Returns:
            Entry ID
        """
        entry_id = self._generate_entry_id()
        timestamp = datetime.utcnow().isoformat()
        
        entry = AuditLogEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            task_id=task_id,
            action_type=action_type,
            target=target,
            status=status,
            level=level,
            details=details or {},
            duration_ms=duration_ms,
            user_id=user_id,
            previous_entry_hash=self._last_entry_hash,
        )
        
        # Calculate hash for this entry
        entry_data = entry.to_dict()
        entry_data.pop('result_hash', None)  # Remove hash field before hashing
        entry_json = json.dumps(entry_data, sort_keys=True)
        entry.result_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        
        # Append to log
        self._append_to_log(entry)
        
        # Update state
        self._last_entry_hash = entry.result_hash
        self._entry_counter += 1
        
        # Check if rotation needed
        if self.auto_rotate and self._should_rotate():
            self._rotate_log()
        
        return entry_id
    
    def log_file_read(
        self,
        task_id: str,
        file_path: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Log file read operation."""
        return self.log(
            task_id=task_id,
            action_type="file_read",
            target=file_path,
            status=status,
            level=AuditLogLevel.INFO,
            details=details or {},
            user_id=user_id,
        )
    
    def log_file_write(
        self,
        task_id: str,
        file_path: str,
        lines_added: int = 0,
        lines_removed: int = 0,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Log file write operation."""
        return self.log(
            task_id=task_id,
            action_type="file_write",
            target=file_path,
            status=status,
            level=AuditLogLevel.WARNING if status != "success" else AuditLogLevel.INFO,
            details={
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                **(details or {}),
            },
            user_id=user_id,
        )
    
    def log_shell_command(
        self,
        task_id: str,
        command: str,
        exit_code: int = 0,
        duration_ms: Optional[int] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Log shell command execution."""
        level = AuditLogLevel.INFO
        if exit_code != 0:
            level = AuditLogLevel.WARNING
            status = "failure"
        
        return self.log(
            task_id=task_id,
            action_type="shell_command",
            target=command,
            status=status,
            level=level,
            details={
                'exit_code': exit_code,
                **(details or {}),
            },
            duration_ms=duration_ms,
            user_id=user_id,
        )
    
    def log_api_call(
        self,
        task_id: str,
        endpoint: str,
        method: str = "GET",
        status_code: int = 200,
        duration_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Log API call."""
        status = "success" if status_code < 400 else "failure"
        level = AuditLogLevel.INFO if status_code < 400 else AuditLogLevel.WARNING
        
        return self.log(
            task_id=task_id,
            action_type="api_call",
            target=f"{method} {endpoint}",
            status=status,
            level=level,
            details={
                'method': method,
                'status_code': status_code,
                **(details or {}),
            },
            duration_ms=duration_ms,
            user_id=user_id,
        )
    
    def log_blocked_action(
        self,
        task_id: str,
        action_type: str,
        target: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Log blocked action."""
        return self.log(
            task_id=task_id,
            action_type=action_type,
            target=target,
            status="blocked",
            level=AuditLogLevel.BLOCKED,
            details={
                'reason': reason,
                **(details or {}),
            },
            user_id=user_id,
        )
    
    def query(self, task_id: Optional[str] = None, action_type: Optional[str] = None) -> List[AuditLogEntry]:
        """
        Query audit log.
        
        Args:
            task_id: Filter by task ID
            action_type: Filter by action type
        
        Returns:
            List of matching entries
        """
        results = []
        
        try:
            if not self.log_path.exists():
                return results
            
            with open(self.log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # Apply filters
                        if task_id and data.get('task_id') != task_id:
                            continue
                        
                        if action_type and data.get('action_type') != action_type:
                            continue
                        
                        # Convert level back to enum
                        if 'level' in data:
                            data['level'] = AuditLogLevel(data['level'])
                        
                        entry = AuditLogEntry(**data)
                        results.append(entry)
                    
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Error parsing audit log entry: {e}")
                        continue
        
        except IOError as e:
            logger.error(f"Error reading audit log: {e}")
        
        return results
    
    def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """Get summary of all actions for a task."""
        entries = self.query(task_id=task_id)
        
        summary = {
            'task_id': task_id,
            'total_actions': len(entries),
            'actions_by_type': {},
            'actions_by_status': {},
            'actions_by_level': {},
            'blocked_actions': 0,
            'failed_actions': 0,
            'total_duration_ms': 0,
        }
        
        for entry in entries:
            # Count by type
            summary['actions_by_type'][entry.action_type] = \
                summary['actions_by_type'].get(entry.action_type, 0) + 1
            
            # Count by status
            summary['actions_by_status'][entry.status] = \
                summary['actions_by_status'].get(entry.status, 0) + 1
            
            # Count by level
            level_str = entry.level.value
            summary['actions_by_level'][level_str] = \
                summary['actions_by_level'].get(level_str, 0) + 1
            
            # Special counts
            if entry.status == "blocked":
                summary['blocked_actions'] += 1
            if entry.status == "failure":
                summary['failed_actions'] += 1
            
            # Total duration
            if entry.duration_ms:
                summary['total_duration_ms'] += entry.duration_ms
        
        return summary
    
    def verify_integrity(self) -> bool:
        """
        Verify audit log integrity by checking hash chain.
        
        Returns:
            True if log is intact, False if tampering detected
        """
        try:
            if not self.log_path.exists():
                return True
            
            previous_hash = None
            
            with open(self.log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # Check hash chain
                        if data.get('previous_entry_hash') != previous_hash:
                            logger.error(
                                f"Hash chain broken at line {line_num}. "
                                f"Expected: {previous_hash}, "
                                f"Got: {data.get('previous_entry_hash')}"
                            )
                            return False
                        
                        # Verify entry hash
                        entry_hash = data.get('result_hash')
                        entry_data = data.copy()
                        entry_data.pop('result_hash', None)
                        
                        calculated_hash = hashlib.sha256(
                            json.dumps(entry_data, sort_keys=True).encode()
                        ).hexdigest()
                        
                        if calculated_hash != entry_hash:
                            logger.error(
                                f"Hash mismatch at line {line_num}. "
                                f"Entry may be tampered."
                            )
                            return False
                        
                        previous_hash = entry_hash
                    
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Error verifying entry at line {line_num}: {e}")
                        return False
            
            logger.info("Audit log integrity verified")
            return True
        
        except IOError as e:
            logger.error(f"Error verifying audit log: {e}")
            return False
    
    def _append_to_log(self, entry: AuditLogEntry) -> None:
        """Append entry to log file (atomic operation)."""
        try:
            with open(self.log_path, 'a') as f:
                f.write(entry.to_json_line() + '\n')
        except IOError as e:
            logger.error(f"Error appending to audit log: {e}")
            raise
    
    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        return f"audit_{self._entry_counter}_{datetime.utcnow().timestamp():.0f}"
    
    def _should_rotate(self) -> bool:
        """Check if log rotation is needed."""
        if not self.log_path.exists():
            return False
        
        return self.log_path.stat().st_size >= self.max_file_size
    
    def _rotate_log(self) -> None:
        """Rotate log file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.log_path.with_name(
            f"{self.log_path.stem}_{timestamp}.jsonl"
        )
        
        try:
            self.log_path.rename(backup_path)
            logger.info(f"Rotated audit log to {backup_path}")
        except IOError as e:
            logger.error(f"Error rotating audit log: {e}")
    
    def _load_previous_state(self) -> None:
        """Load state from previous log file."""
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                
                if lines:
                    # Get last entry to find last hash
                    last_line = lines[-1].strip()
                    if last_line:
                        data = json.loads(last_line)
                        self._last_entry_hash = data.get('result_hash')
                    
                    self._entry_counter = len(lines)
        
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Error loading previous audit log state: {e}")

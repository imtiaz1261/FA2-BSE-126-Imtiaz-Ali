"""
Human Approval Gateway for Code Alpha Safety

Manages approval workflows for risky actions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ApprovalRequest:
    """Request for human approval."""
    
    request_id: str
    task_id: str
    action_type: str
    target: str
    risk_level: str
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_by: Optional[str] = None
    approval_timestamp: Optional[str] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if approval request has expired."""
        if self.expires_at is None:
            return False
        
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.utcnow() > expires
        except (ValueError, TypeError):
            return False
    
    def approve(self, approved_by: str) -> None:
        """Mark as approved."""
        self.status = ApprovalStatus.APPROVED
        self.approved_by = approved_by
        self.approval_timestamp = datetime.utcnow().isoformat()
    
    def reject(self, rejection_reason: str) -> None:
        """Mark as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.rejection_reason = rejection_reason
    
    def cancel(self) -> None:
        """Mark as cancelled."""
        self.status = ApprovalStatus.CANCELLED
    
    def expire(self) -> None:
        """Mark as expired."""
        self.status = ApprovalStatus.EXPIRED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data


class ApprovalCallbacks:
    """Callbacks for approval notifications."""
    
    def __init__(self):
        """Initialize callbacks."""
        self.callbacks: List[Callable[[ApprovalRequest], None]] = []
    
    def register(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register a callback."""
        self.callbacks.append(callback)
    
    def notify(self, request: ApprovalRequest) -> None:
        """Notify all registered callbacks."""
        for callback in self.callbacks:
            try:
                callback(request)
            except Exception as e:
                logger.error(f"Error in approval callback: {e}")


class ApprovalGateway:
    """
    Gateway for managing human approvals.
    
    Handles:
    - Request creation and routing
    - Status tracking
    - Expiration handling
    - Approval escalation
    """
    
    def __init__(
        self,
        default_timeout_seconds: int = 3600,
        auto_reject_expired: bool = True,
    ):
        """
        Initialize approval gateway.
        
        Args:
            default_timeout_seconds: Default approval timeout (1 hour)
            auto_reject_expired: Whether to auto-reject expired requests
        """
        self.default_timeout_seconds = default_timeout_seconds
        self.auto_reject_expired = auto_reject_expired
        
        # Track approval requests
        self.requests: Dict[str, ApprovalRequest] = {}
        
        # Callbacks for notifications
        self.callbacks = ApprovalCallbacks()
        
        logger.info("ApprovalGateway initialized")
    
    def request_approval(
        self,
        task_id: str,
        action_type: str,
        target: str,
        risk_level: str,
        reason: str,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        Request approval for an action.
        
        Args:
            task_id: Task ID
            action_type: Type of action
            target: Target of action
            risk_level: Risk level
            reason: Reason for approval request
            timeout_seconds: Custom timeout
            metadata: Additional metadata
        
        Returns:
            ApprovalRequest object
        """
        request_id = str(uuid4())
        timeout = timeout_seconds or self.default_timeout_seconds
        
        expires_at = (
            datetime.utcnow() + timedelta(seconds=timeout)
        ).isoformat()
        
        request = ApprovalRequest(
            request_id=request_id,
            task_id=task_id,
            action_type=action_type,
            target=target,
            risk_level=risk_level,
            reason=reason,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        
        self.requests[request_id] = request
        
        # Notify callbacks
        self.callbacks.notify(request)
        
        logger.info(
            f"Approval requested: {action_type} on {target} "
            f"(expires in {timeout}s)",
            extra={'task_id': task_id, 'request_id': request_id}
        )
        
        return request
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID."""
        return self.requests.get(request_id)
    
    def get_pending_requests(self, task_id: Optional[str] = None) -> List[ApprovalRequest]:
        """Get pending approval requests."""
        pending = [
            r for r in self.requests.values()
            if r.status == ApprovalStatus.PENDING and not r.is_expired()
        ]
        
        if task_id:
            pending = [r for r in pending if r.task_id == task_id]
        
        return pending
    
    def approve(self, request_id: str, approved_by: str) -> bool:
        """
        Approve a request.
        
        Returns:
            True if approved successfully, False otherwise
        """
        request = self.get_request(request_id)
        if not request:
            logger.warning(f"Approval request not found: {request_id}")
            return False
        
        if request.status != ApprovalStatus.PENDING:
            logger.warning(
                f"Cannot approve request in status {request.status}: {request_id}"
            )
            return False
        
        if request.is_expired():
            request.expire()
            logger.warning(f"Approval request expired: {request_id}")
            return False
        
        request.approve(approved_by)
        
        logger.info(
            f"Approval granted: {request.action_type} on {request.target}",
            extra={'request_id': request_id, 'approved_by': approved_by}
        )
        
        return True
    
    def reject(self, request_id: str, reason: str) -> bool:
        """
        Reject a request.
        
        Returns:
            True if rejected successfully, False otherwise
        """
        request = self.get_request(request_id)
        if not request:
            logger.warning(f"Approval request not found: {request_id}")
            return False
        
        if request.status != ApprovalStatus.PENDING:
            logger.warning(
                f"Cannot reject request in status {request.status}: {request_id}"
            )
            return False
        
        request.reject(reason)
        
        logger.info(
            f"Approval rejected: {request.action_type} on {request.target}",
            extra={'request_id': request_id, 'reason': reason}
        )
        
        return True
    
    def cancel(self, request_id: str) -> bool:
        """Cancel a request."""
        request = self.get_request(request_id)
        if not request:
            return False
        
        if request.status == ApprovalStatus.PENDING:
            request.cancel()
            return True
        
        return False
    
    def check_expiration(self) -> List[str]:
        """
        Check and handle expired requests.
        
        Returns:
            List of expired request IDs
        """
        expired_ids = []
        
        for request_id, request in self.requests.items():
            if (
                request.status == ApprovalStatus.PENDING and
                request.is_expired()
            ):
                if self.auto_reject_expired:
                    request.expire()
                    logger.warning(f"Auto-expired approval request: {request_id}")
                
                expired_ids.append(request_id)
        
        return expired_ids
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        by_status = {}
        for request in self.requests.values():
            status = request.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            'total_requests': len(self.requests),
            'by_status': by_status,
            'pending_count': len(self.get_pending_requests()),
            'expired_count': len(self.check_expiration()),
        }
    
    def cleanup_completed(self) -> int:
        """
        Clean up completed/expired requests.
        
        Returns:
            Number of cleaned up requests
        """
        to_delete = []
        
        for request_id, request in self.requests.items():
            if request.status in [
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.EXPIRED,
                ApprovalStatus.CANCELLED,
            ]:
                # Keep for 1 hour after completion
                completed_time = request.approval_timestamp or request.requested_at
                try:
                    completed = datetime.fromisoformat(completed_time)
                    if datetime.utcnow() - completed > timedelta(hours=1):
                        to_delete.append(request_id)
                except (ValueError, TypeError):
                    pass
        
        for request_id in to_delete:
            del self.requests[request_id]
        
        logger.info(f"Cleaned up {len(to_delete)} completed approval requests")
        
        return len(to_delete)

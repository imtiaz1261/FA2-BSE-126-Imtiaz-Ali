"""
Admin authorization dependencies for FastAPI.

Provides:
- require_admin: Dependency that checks if user has admin role
"""
import logging

from fastapi import Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models import User, UserRole

logger = logging.getLogger(__name__)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to enforce admin role.

    Call this in any route that requires admin privileges.
    Returns 403 if user lacks admin role.

    Args:
        current_user: Authenticated user from JWT

    Returns:
        User object if admin role verified

    Raises:
        HTTPException (403): If user is not an admin

    Example:
        @router.get("/admin/users")
        async def list_users(admin=Depends(require_admin)):
            ...
    """
    if current_user.role != UserRole.admin:
        logger.warning(
            f"Non-admin user {current_user.id} ({current_user.email}) "
            f"attempted to access admin endpoint"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "ADMIN_ACCESS_REQUIRED",
                    "message": "Administrator privileges are required to access this resource.",
                }
            },
        )

    return current_user

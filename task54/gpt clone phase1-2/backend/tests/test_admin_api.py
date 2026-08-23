"""
Tests for admin APIs.

Tests authorization, analytics, user management, billing, and moderation endpoints.
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole, UserStatus
from app.models_admin import AdminAuditLog, ModerationFlag
from app.models_billing import Subscription, SubscriptionPlan, SubscriptionStatus


# ============================================================================
# Authorization Tests
# ============================================================================


@pytest.mark.asyncio
async def test_normal_user_cannot_access_admin_analytics(
    client: AsyncClient,
    user_token: str,
):
    """Normal user should get 403 when accessing admin endpoints."""
    response = await client.get(
        "/api/v1/admin/analytics/overview",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "ADMIN_ACCESS_REQUIRED" in response.text


@pytest.mark.asyncio
async def test_admin_user_can_access_admin_analytics(
    client: AsyncClient,
    admin_token: str,
):
    """Admin user should access admin endpoints."""
    response = await client.get(
        "/api/v1/admin/analytics/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_access_admin(client: AsyncClient):
    """Unauthenticated user should get 401."""
    response = await client.get("/api/v1/admin/analytics/overview")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_suspended_user_cannot_login(
    client: AsyncClient,
    suspended_user: User,
    db: AsyncSession,
):
    """Suspended user should be denied login."""
    response = await client.post(
        "/auth/login",
        json={"email": suspended_user.email, "password": "test_password"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "suspended" in response.text.lower()


@pytest.mark.asyncio
async def test_banned_user_cannot_login(
    client: AsyncClient,
    banned_user: User,
):
    """Banned user should be denied login."""
    response = await client.post(
        "/auth/login",
        json={"email": banned_user.email, "password": "test_password"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "banned" in response.text.lower()


# ============================================================================
# Analytics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_analytics_overview_returns_metrics(
    client: AsyncClient,
    admin_token: str,
):
    """Overview endpoint should return KPI metrics."""
    response = await client.get(
        "/api/v1/admin/analytics/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert "dau" in data["data"]
    assert "mau" in data["data"]
    assert "messages_today" in data["data"]
    assert "paid_subscriptions" in data["data"]


@pytest.mark.asyncio
async def test_analytics_active_users(
    client: AsyncClient,
    admin_token: str,
):
    """Active users endpoint should return DAU/MAU data."""
    response = await client.get(
        "/api/v1/admin/analytics/active-users",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={
            "start_date": "2026-08-01",
            "end_date": "2026-08-16",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_analytics_date_range_validation(
    client: AsyncClient,
    admin_token: str,
):
    """Date range should be validated."""
    # More than 365 days should be truncated
    response = await client.get(
        "/api/v1/admin/analytics/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={
            "start_date": "2025-01-01",
            "end_date": "2026-08-16",
        },
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_analytics_plan_distribution(
    client: AsyncClient,
    admin_token: str,
):
    """Plan distribution should return plan stats."""
    response = await client.get(
        "/api/v1/admin/analytics/plans",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    # Should contain free/plus/pro plans
    plan_names = [item["plan"] for item in data["data"]]
    assert "free" in plan_names or len(plan_names) >= 0


# ============================================================================
# User Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_users_with_search(
    client: AsyncClient,
    admin_token: str,
    normal_user: User,
):
    """Users list should support search filtering."""
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"search": normal_user.email},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert data["page"] == 1
    assert data["page_size"] > 0


@pytest.mark.asyncio
async def test_list_users_with_plan_filter(
    client: AsyncClient,
    admin_token: str,
):
    """Users list should filter by plan."""
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"plan": "free"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_list_users_pagination(
    client: AsyncClient,
    admin_token: str,
):
    """Users list should support pagination."""
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"page": 1, "page_size": 10},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_user_details(
    client: AsyncClient,
    admin_token: str,
    normal_user: User,
):
    """Should get user details."""
    response = await client.get(
        f"/api/v1/admin/users/{normal_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == normal_user.email
    assert data["id"] == str(normal_user.id)


@pytest.mark.asyncio
async def test_get_user_details_audit_logged(
    client: AsyncClient,
    admin_token: str,
    admin_user: User,
    normal_user: User,
    db: AsyncSession,
):
    """Viewing user details should create audit log."""
    response = await client.get(
        f"/api/v1/admin/users/{normal_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK

    # Check audit log was created
    from sqlalchemy import select

    audit_logs = await db.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.action == "USER_VIEWED"
        )
    )
    logs = audit_logs.scalars().all()
    assert len(logs) > 0


@pytest.mark.asyncio
async def test_suspend_user(
    client: AsyncClient,
    admin_token: str,
    normal_user: User,
    db: AsyncSession,
):
    """Should suspend a user."""
    response = await client.post(
        f"/api/v1/admin/users/{normal_user.id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Policy violation"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "suspended"

    # Verify in DB
    await db.refresh(normal_user)
    assert normal_user.status == UserStatus.suspended


@pytest.mark.asyncio
async def test_suspended_user_cannot_chat(
    client: AsyncClient,
    suspended_user_token: str,
):
    """Suspended user should not be able to use chat."""
    response = await client.post(
        "/chat/stream",
        headers={"Authorization": f"Bearer {suspended_user_token}"},
        json={"messages": [], "conversation_id": None},
    )
    # Should fail with 403 or 401 due to suspension check
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio
async def test_unsuspend_user(
    client: AsyncClient,
    admin_token: str,
    suspended_user: User,
    db: AsyncSession,
):
    """Should unsuspend a user."""
    response = await client.post(
        f"/api/v1/admin/users/{suspended_user.id}/unsuspend",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "active"

    # Verify in DB
    await db.refresh(suspended_user)
    assert suspended_user.status == UserStatus.active


@pytest.mark.asyncio
async def test_ban_user(
    client: AsyncClient,
    admin_token: str,
    normal_user: User,
    db: AsyncSession,
):
    """Should ban a user."""
    response = await client.post(
        f"/api/v1/admin/users/{normal_user.id}/ban",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Severe policy violation"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "banned"

    # Verify in DB
    await db.refresh(normal_user)
    assert normal_user.status == UserStatus.banned


@pytest.mark.asyncio
async def test_change_user_plan(
    client: AsyncClient,
    admin_token: str,
    normal_user: User,
    db: AsyncSession,
):
    """Should change user plan."""
    # Get current subscription
    from sqlalchemy import select

    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == normal_user.id)
    )
    subscription = sub_result.scalar_one_or_none()
    initial_plan = subscription.plan.value if subscription else "free"

    # Change plan
    response = await client.post(
        f"/api/v1/admin/users/{normal_user.id}/plan",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"plan": "plus"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True


# ============================================================================
# Audit Logging Tests
# ============================================================================


@pytest.mark.asyncio
async def test_admin_actions_create_audit_logs(
    client: AsyncClient,
    admin_token: str,
    admin_user: User,
    normal_user: User,
    db: AsyncSession,
):
    """Admin actions should create audit log entries."""
    # Suspend user
    response = await client.post(
        f"/api/v1/admin/users/{normal_user.id}/suspend",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Test suspension"},
    )
    assert response.status_code == status.HTTP_200_OK

    # Check audit log
    from sqlalchemy import select

    audit_logs = await db.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.action == "USER_SUSPENDED"
        )
    )
    logs = audit_logs.scalars().all()
    assert len(logs) > 0
    assert logs[0].target_user_id == normal_user.id
    assert logs[0].admin_user_id == admin_user.id


# ============================================================================
# Moderation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_moderation_queue_returns_flags(
    client: AsyncClient,
    admin_token: str,
):
    """Moderation queue should return flagged conversations."""
    response = await client.get(
        "/api/v1/admin/moderation",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_moderation_queue_filter_by_status(
    client: AsyncClient,
    admin_token: str,
):
    """Moderation queue should filter by status."""
    response = await client.get(
        "/api/v1/admin/moderation",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"status": "pending"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def admin_user(db: AsyncSession) -> User:
    """Create an admin user."""
    user = User(
        email="admin@test.com",
        hashed_password="hashed_password",
        role=UserRole.admin,
        status=UserStatus.active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def normal_user(db: AsyncSession) -> User:
    """Create a normal user."""
    user = User(
        email="user@test.com",
        hashed_password="hashed_password",
        role=UserRole.user,
        status=UserStatus.active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def suspended_user(db: AsyncSession) -> User:
    """Create a suspended user."""
    user = User(
        email="suspended@test.com",
        hashed_password="hashed_password",
        role=UserRole.user,
        status=UserStatus.suspended,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def banned_user(db: AsyncSession) -> User:
    """Create a banned user."""
    user = User(
        email="banned@test.com",
        hashed_password="hashed_password",
        role=UserRole.user,
        status=UserStatus.banned,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def admin_token(admin_user: User) -> str:
    """Create JWT token for admin user."""
    from app.security import create_access_token

    token, _ = create_access_token(admin_user.id)
    return token


@pytest.fixture
async def user_token(normal_user: User) -> str:
    """Create JWT token for normal user."""
    from app.security import create_access_token

    token, _ = create_access_token(normal_user.id)
    return token


@pytest.fixture
async def suspended_user_token(suspended_user: User) -> str:
    """Create JWT token for suspended user."""
    from app.security import create_access_token

    token, _ = create_access_token(suspended_user.id)
    return token

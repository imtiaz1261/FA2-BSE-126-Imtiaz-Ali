# Admin & Analytics Dashboard - Production Implementation Guide

## Overview

Complete, production-ready admin dashboard for AI Chat SaaS platform with:
- Role-based access control (RBAC)
- Platform analytics (DAU/MAU, messages, tokens, cost, churn, retention)
- User management (search, suspend, ban, plan changes)
- Billing administration (refunds, plan changes)
- Content moderation (flag review, approvals)
- Complete audit logging

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Admin Dashboard                    │
│  (AdminLayout, Overview, Users, Analytics, Moderation, Billing)
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Admin API Routers                     │
│  /api/v1/admin/analytics/* (9 endpoints)                   │
│  /api/v1/admin/users/* (6 endpoints)                       │
│  /api/v1/admin/billing/* (2 endpoints)                     │
│  /api/v1/admin/moderation/* (4 endpoints)                  │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│            Authorization & Service Layer                    │
│  require_admin() → Dependency injection                     │
│  AnalyticsService → Query aggregation                       │
│  AdminUserService → User operations                         │
│  AdminBillingService → Stripe integration                   │
│  ModerationService → Flag management                        │
│  AdminAuditService → Audit trail                            │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL + Redis + Stripe                    │
│  admin_audit_logs, moderation_flags                         │
│  model_request_logs, daily_platform_metrics                 │
│  users (role, status), subscriptions                        │
└─────────────────────────────────────────────────────────────┘
```

## Setup & Configuration

### 1. Database Migrations

Apply migration 0006_admin_system:
```bash
cd backend
alembic upgrade head
```

Creates:
- `users.role` (UserRole enum: user, admin)
- `users.status` (UserStatus enum: active, suspended, banned)
- `admin_audit_logs` (action tracking)
- `moderation_flags` (content review queue)
- `model_request_logs` (LLM performance)
- `daily_platform_metrics` (aggregated stats)

### 2. Create Admin User

```python
from app.models import User, UserRole, UserStatus
from app.security import hash_password

admin = User(
    email="admin@example.com",
    hashed_password=hash_password("secure_password"),
    name="Admin User",
    role=UserRole.admin,
    status=UserStatus.active,
    is_verified=True,
)
db.add(admin)
await db.commit()
```

### 3. Environment Variables

```bash
# Already configured in .env.example
# No additional variables required
```

## API Endpoints

### Analytics (`/api/v1/admin/analytics`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/overview` | GET | KPIs: DAU, MAU, messages, tokens, cost, subscriptions, churn |
| `/active-users` | GET | Daily DAU/MAU timeseries |
| `/messages` | GET | Message volume per day |
| `/tokens` | GET | Input/output tokens per day |
| `/cost` | GET | Estimated AI cost per day |
| `/plans` | GET | Plan distribution (free/plus/pro) |
| `/churn` | GET | Monthly churn rate |
| `/retention` | GET | Weekly retention cohorts |
| `/models` | GET | Model performance (requests, latency, cost) |

**Query Parameters:**
- `start_date`: ISO format (optional, default: 30 days ago)
- `end_date`: ISO format (optional, default: today)
- Automatic validation: max 365 days

### User Management (`/api/v1/admin/users`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List users (search, filter, paginate) |
| `/{user_id}` | GET | User details (account, subscription, usage) |
| `/{user_id}/suspend` | POST | Suspend user (requires reason) |
| `/{user_id}/unsuspend` | POST | Restore suspended user |
| `/{user_id}/ban` | POST | Permanently ban user (requires reason) |
| `/{user_id}/plan` | POST | Change subscription plan |

**List Users Query Parameters:**
- `search`: Email or name
- `plan`: free, plus, pro
- `status`: active, suspended, banned
- `start_date`, `end_date`: Signup date range
- `page`, `page_size`: Pagination
- `sort`, `order`: Sorting options

### Billing (`/api/v1/admin/billing`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/users/{user_id}/plan` | POST | Change plan (syncs with Stripe) |
| `/users/{user_id}/refund` | POST | Issue refund (full or partial) |

**Plan Change:**
- Validates with Stripe
- Cancels at period end for downgrades
- Creates subscription for upgrades

**Refund:**
- Full refund: `amount: null`
- Partial refund: `amount: 19.99`
- Requires `payment_intent_id` and `reason`

### Moderation (`/api/v1/admin/moderation`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Moderation queue (filter, paginate) |
| `/{flag_id}` | GET | Flag details (user, conversation, messages) |
| `/{flag_id}/approve` | POST | Approve flag (content is safe) |
| `/{flag_id}/ban` | POST | Ban user (confirm violation) |

**Queue Filters:**
- `status`: pending, approved, banned, dismissed
- `severity`: low, medium, high, critical
- `category`: self_harm, violence, harassment, etc.

## Authorization

### Role Check

All admin endpoints check `require_admin()` dependency:

```python
from app.admin_dependencies import require_admin

@router.get("/admin/users")
async def list_users(admin: User = Depends(require_admin)):
    # admin.role == UserRole.admin (verified)
    ...
```

### What Gets Blocked

✗ Normal user accesses `/api/v1/admin/*` → HTTP 403
✗ Unauthenticated request → HTTP 401
✗ Suspended user login → HTTP 403
✗ Banned user login → HTTP 403

### What's Allowed

✓ Admin user logged in → Full access
✓ Normal user chat → Limited to own data
✓ Audit log → Records all admin actions

## Audit Logging

Every sensitive action creates an `AdminAuditLog` entry:

```python
{
    "id": "uuid",
    "admin_user_id": "uuid",
    "target_user_id": "uuid",  # nullable
    "action": "USER_SUSPENDED",
    "reason": "Policy violation",
    "metadata": {"...": "..."},
    "created_at": "2026-08-16T12:00:00Z"
}
```

### Tracked Actions

- `USER_VIEWED` - Admin viewed user details
- `USER_SUSPENDED` - User suspended
- `USER_UNSUSPENDED` - User restored
- `USER_BANNED` - User permanently banned
- `PLAN_CHANGED` - Subscription plan modified
- `REFUND_ISSUED` - Payment refunded
- `MODERATION_APPROVED` - Flag approved
- `MODERATION_BANNED` - User banned from flag

**Query audit logs:**
```python
GET /api/v1/admin/audit-logs?admin_id=uuid&action=USER_SUSPENDED
```

## User Status Management

### Status Enum

```python
class UserStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    banned = "banned"
```

### Enforcement Points

1. **Login** (`/auth/login`)
   ```python
   if user.status == UserStatus.banned:
       raise HTTPException(403, "This account has been banned")
   if user.status == UserStatus.suspended:
       raise HTTPException(403, "This account has been suspended")
   ```

2. **Chat** (any protected endpoint)
   - Implicit: User token creation checks `is_active`
   - Database: Enforce in query filters

3. **Audit** (AdminAuditLog)
   - All changes create immutable log entries
   - Admins cannot modify/delete logs

## Frontend Routes

### Protected Routes

```
/admin → AdminOverview
  ↓ User role != admin → redirect to /
  ↓ Not authenticated → redirect to /login

/admin/analytics → Analytics pages
/admin/users → User search & list
/admin/users/:id → User details
/admin/moderation → Moderation queue
/admin/billing → Billing management
```

### Route Guard

```typescript
<AdminRoute>
  <AdminOverview />
</AdminRoute>
```

Checks: `user.role === "admin"` on client (+ server-side enforcement)

## Common Workflows

### Workflow 1: Suspend a Policy Violator

1. Admin searches user on `/admin/users`
2. Clicks suspend
3. Enters reason
4. `POST /api/v1/admin/users/{id}/suspend` → 200
5. AdminAuditLog created
6. User status = suspended
7. User cannot login
8. Next login attempt: 403 "suspended"

### Workflow 2: Review Moderation Flag

1. Admin views `/admin/moderation`
2. Queue shows pending flags
3. Admin clicks flag
4. Details panel shows:
   - Flag category, severity, reason
   - User email, conversation title
   - Recent messages from conversation
5. Admin approves or bans:
   - `POST /api/v1/admin/moderation/{flag_id}/approve` → Creates audit log
   - `POST /api/v1/admin/moderation/{flag_id}/ban` → Bans user + creates audit log

### Workflow 3: Issue Refund

1. Admin navigates to `/admin/billing`
2. Searches for user
3. Selects "Issue Refund"
4. Enters:
   - Stripe payment intent ID
   - Amount (optional, null = full refund)
   - Reason
5. `POST /api/v1/admin/billing/users/{id}/refund` → Processes via Stripe API
6. AdminAuditLog tracks refund details

### Workflow 4: Change User Plan

1. Admin views user on `/admin/users/:id`
2. Clicks "Change Plan"
3. Selects new plan (free/plus/pro)
4. `POST /api/v1/admin/users/{id}/plan`
5. Backend:
   - Gets Stripe subscription
   - Updates via Stripe API
   - Synchronizes local DB
   - Creates audit log

## Analytics Calculation

### DAU (Daily Active Users)
```sql
COUNT(DISTINCT user_id) 
FROM messages 
WHERE DATE(created_at) = today
```

### MAU (Monthly Active Users)
```sql
COUNT(DISTINCT user_id)
FROM messages
WHERE created_at >= 30 days ago
```

### Churn Rate
```
cancelled_subscriptions / total_paid_subscriptions * 100
```

### Retention Cohort
```
Weekly cohorts showing:
- Users who signed up in week N
- How many are still active in weeks N+0, N+1, N+2, N+3
```

### Cost Calculation
```
SUM(estimated_cost)
FROM model_request_logs
WHERE created_at IN date_range
```

## Testing

Run admin API tests:
```bash
cd backend
pytest tests/test_admin_api.py -v
```

Tests cover:
- Authorization (normal user denied, admin allowed)
- Analytics calculations
- User management
- Billing operations
- Audit logging
- Moderation actions
- Stripe error handling

## Performance Considerations

### Optimization

1. **Analytics Caching** (optional)
   - Cache 24-hour analytics in Redis
   - TTL: 1 hour
   - Invalidate on new messages/model logs

2. **User Search**
   - Indexed: email, name, plan, status, created_at
   - Full-text search on email/name
   - Pagination: default 25 users/page

3. **Audit Logs**
   - Append-only table
   - Index: admin_user_id, target_user_id, action, created_at
   - Query: 30-day window

4. **Model Request Logs**
   - Store only recent data (90 days)
   - Aggregate to daily_platform_metrics
   - Background job: daily aggregation

### Scaling Path

**Phase 2: High Volume**
- Move analytics to time-series DB (InfluxDB, TimescaleDB)
- Cache all dashboard queries for 5 minutes
- Batch audit log writes

**Phase 3: Multi-Tenant**
- Add `admin_for_org_id` to access control
- Separate audit logs per org
- Org-scoped analytics queries

## Security Checklist

✓ Admin role verified on every endpoint
✓ Frontend checks only for UX (server validates)
✓ Sensitive actions logged to immutable audit table
✓ Stripe secrets never exposed to frontend
✓ Suspended/banned users denied at login
✓ Date ranges validated (max 365 days)
✓ SQL injection prevented (ORM + parameterized queries)
✓ CSRF protection via session middleware
✓ Rate limiting on auth endpoints
✓ No PII in logs (password hashes excluded)
✓ All monetary operations recorded

## Troubleshooting

### "403 ADMIN_ACCESS_REQUIRED"
- User role is `user` not `admin`
- Create admin user (see Setup section)
- Verify JWT token contains correct role

### "User already suspended"
- Suspension is idempotent
- Unsuspend first: `POST /api/v1/admin/users/{id}/unsuspend`

### Stripe refund fails
- Verify payment_intent_id is correct
- Check Stripe API key in `.env`
- Ensure payment is in Stripe account

### Analytics show zero data
- Check if messages exist in database
- Verify date range is correct
- Model logs should exist for token/cost data

## Files Modified

### Backend
- `alembic/versions/0006_admin_system.py` - Migrations
- `app/models.py` - Added role, status to User
- `app/models_admin.py` - New admin models
- `app/admin_dependencies.py` - Authorization
- `app/schemas_admin.py` - API schemas
- `app/services/analytics_service.py` - Analytics
- `app/services/admin_user_service.py` - User operations
- `app/services/admin_audit_service.py` - Audit logging
- `app/services/admin_billing_service.py` - Billing ops
- `app/services/moderation_service.py` - Moderation
- `app/routers/admin_*.py` - 4 API routers
- `app/main.py` - Route registration
- `tests/test_admin_api.py` - Tests

### Frontend
- `src/services/adminApi.ts` - API client
- `src/components/admin/*.tsx` - Components
- `src/pages/admin/*.tsx` - Pages
- `src/App.tsx` - Routing

## Next Steps

### Optional Enhancements
1. Real-time analytics dashboard (WebSocket)
2. Advanced moderation (ML classification)
3. Usage forecasting
4. Automated abuse detection
5. Custom admin roles
6. Admin activity dashboard

### Integration Points
- Connect to real LLM API (OpenAI/Anthropic)
- Set up Celery for background jobs
- Configure real Stripe account
- Set up email notifications for admins

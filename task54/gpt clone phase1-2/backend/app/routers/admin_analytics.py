"""
Admin analytics API endpoints.

Provides platform-wide analytics for admin dashboard:
- DAU / MAU
- Message volume
- Token usage
- Cost tracking
- Plan distribution
- Churn & retention
- Model performance
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_dependencies import require_admin
from app.database import get_db
from app.schemas_admin import AnalyticsResponse, OverviewMetrics, ModelPerformanceResponse
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/analytics", tags=["Admin Analytics"])


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse ISO format date string."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def _get_date_range(
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[datetime, datetime]:
    """
    Get date range with defaults.

    If not provided, defaults to last 30 days.
    """
    end = _parse_date(end_date) or datetime.utcnow()
    start = _parse_date(start_date) or (end - timedelta(days=30))

    # Validate range (don't allow more than 1 year)
    if (end - start).days > 365:
        start = end - timedelta(days=365)

    return start, end


@router.get("/overview")
async def analytics_overview(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get high-level platform KPIs.

    Returns:
    - DAU, MAU
    - Messages today
    - Token usage today
    - Estimated AI cost
    - Active paid subscriptions
    - Monthly churn rate

    Query Parameters:
    - start_date: ISO format (optional, default: 30 days ago)
    - end_date: ISO format (optional, default: today)
    """
    try:
        start, end = _get_date_range(start_date, end_date)

        overview = await AnalyticsService.get_overview(db, start, end)

        return {
            "data": overview,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get analytics overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/active-users")
async def analytics_active_users(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """
    Get DAU and MAU for each day in range.

    Returns list of daily data points with:
    - date: ISO format date
    - dau: Daily Active Users
    - mau: Monthly Active Users
    """
    try:
        start, end = _get_date_range(start_date, end_date)

        data = await AnalyticsService.get_active_users(db, start, end)

        return AnalyticsResponse(data=data)

    except Exception as e:
        logger.error(f"Failed to get active users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/messages")
async def analytics_messages(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """
    Get message volume per day.

    Returns list of daily data points with:
    - date: ISO format date
    - messages: Message count
    """
    try:
        start, end = _get_date_range(start_date, end_date)

        data = await AnalyticsService.get_messages(db, start, end)

        return AnalyticsResponse(data=data)

    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/tokens")
async def analytics_tokens(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """
    Get token usage per day.

    Returns list of daily data points with:
    - date: ISO format date
    - input_tokens: Input tokens
    - output_tokens: Output tokens
    - total_tokens: Total tokens
    """
    try:
        start, end = _get_date_range(start_date, end_date)

        data = await AnalyticsService.get_tokens(db, start, end)

        return AnalyticsResponse(data=data)

    except Exception as e:
        logger.error(f"Failed to get tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/cost")
async def analytics_cost(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get estimated AI cost per day.

    Returns:
    - data: List of daily cost data points
    - total_cost: Sum of all costs in period
    """
    try:
        start, end = _get_date_range(start_date, end_date)

        result = await AnalyticsService.get_cost(db, start, end)

        return {
            **result,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get cost: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/plans")
async def analytics_plans(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """
    Get subscription plan distribution.

    Returns list of plan data points with:
    - plan: Plan name (free, plus, pro)
    - users: User count on plan
    - percentage: Percentage of total
    """
    try:
        data = await AnalyticsService.get_plan_distribution(db)

        return AnalyticsResponse(data=data)

    except Exception as e:
        logger.error(f"Failed to get plan distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/churn")
async def analytics_churn(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """
    Get monthly churn rate (simplified).

    Formula: cancelled paid subscriptions / total paid subscriptions * 100

    Returns list of monthly data points with:
    - month: ISO format month (YYYY-MM)
    - churn_rate: Percentage
    """
    try:
        # Simplified: return current churn
        churn_rate = await AnalyticsService._calculate_monthly_churn(db)

        current_month = datetime.utcnow().strftime("%Y-%m")
        data = [{"month": current_month, "churn_rate": churn_rate}]

        return AnalyticsResponse(data=data)

    except Exception as e:
        logger.error(f"Failed to get churn: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/retention")
async def analytics_retention(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get retention cohorts (simplified weekly).

    Returns cohort analysis showing user retention over 4 weeks:
    - cohort: Signup week (YYYY-MM-DD)
    - users: Users in cohort
    - week_0-3: Users active in each week
    """
    try:
        start, end = _get_date_range(start_date, end_date)

        cohorts = await AnalyticsService.get_retention(db, start, end)

        return {
            "cohorts": cohorts,
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get retention: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )


@router.get("/models")
async def analytics_models(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ModelPerformanceResponse:
    """
    Get model performance statistics.

    Returns performance metrics per model:
    - model: Model name
    - requests: Request count
    - success_rate: Success percentage
    - error_rate: Error percentage
    - latency metrics (avg, p50, p95, p99)
    - token usage (input, output, total)
    - estimated_cost
    """
    try:
        start, end = _get_date_range(start_date, end_date)

        models = await AnalyticsService.get_model_performance(db, start, end)

        return ModelPerformanceResponse(models=models)

    except Exception as e:
        logger.error(f"Failed to get model performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )

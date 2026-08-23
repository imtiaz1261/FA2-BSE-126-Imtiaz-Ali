"""
Analytics aggregation service for admin dashboard.

Handles:
- DAU / MAU calculations
- Message volume
- Token usage
- Cost tracking
- Plan distribution
- Churn & retention
- Model performance
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from app.models import Conversation, Message, MessageRole, User, UserStatus
from app.models_billing import Subscription, SubscriptionPlan, SubscriptionStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_admin import DailyPlatformMetric, ModelRequestLog
from app.models_billing import Subscription, SubscriptionPlan, SubscriptionStatus

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for calculating platform analytics."""

    @staticmethod
    async def get_overview(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """
        Get high-level platform KPIs for date range.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dict with DAU, MAU, messages, tokens, cost, subscriptions, churn
        """
        try:
            # Get today's metrics
            today = datetime.utcnow().date()

            # DAU: Unique users with messages today
            dau_stmt = select(func.count(func.distinct(Message.user_id))).where(
                func.date(Message.created_at) == today
            )
            dau = await db.scalar(dau_stmt) or 0

            # MAU: Unique users in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            mau_stmt = select(func.count(func.distinct(Message.user_id))).where(
                Message.created_at >= thirty_days_ago
            )
            mau = await db.scalar(mau_stmt) or 0

            # Messages today
            messages_today_stmt = select(func.count(Message.id)).where(
                (Message.role == MessageRole.user)
                & (func.date(Message.created_at) == today)
            )
            messages_today = await db.scalar(messages_today_stmt) or 0

            # Tokens today (from model logs)
            tokens_stmt = select(
                func.sum(ModelRequestLog.input_tokens),
                func.sum(ModelRequestLog.output_tokens),
            ).where(func.date(ModelRequestLog.created_at) == today)

            input_tokens, output_tokens = await db.execute(tokens_stmt)
            input_tokens = input_tokens or 0
            output_tokens = output_tokens or 0
            tokens_today = input_tokens + output_tokens

            # Cost today
            cost_stmt = select(func.sum(ModelRequestLog.estimated_cost)).where(
                func.date(ModelRequestLog.created_at) == today
            )
            cost_today = float(await db.scalar(cost_stmt) or 0)

            # Paid subscriptions
            paid_subs_stmt = select(func.count(Subscription.id)).where(
                (Subscription.plan.in_([SubscriptionPlan.plus, SubscriptionPlan.pro]))
                & (Subscription.status == SubscriptionStatus.active)
            )
            paid_subscriptions = await db.scalar(paid_subs_stmt) or 0

            # Monthly churn rate (simplified)
            churn_rate = await AnalyticsService._calculate_monthly_churn(db)

            # New users today
            new_users_stmt = select(func.count(User.id)).where(
                func.date(User.created_at) == today
            )
            new_users_today = await db.scalar(new_users_stmt) or 0

            return {
                "dau": dau,
                "mau": mau,
                "messages_today": messages_today,
                "tokens_today": tokens_today,
                "estimated_cost_today": cost_today,
                "paid_subscriptions": paid_subscriptions,
                "monthly_churn_rate": churn_rate,
                "new_users_today": new_users_today,
            }

        except Exception as e:
            logger.error(f"Failed to calculate overview: {e}")
            return {}

    @staticmethod
    async def get_active_users(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """
        Get DAU and MAU for each day in range.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of daily DAU/MAU data points
        """
        try:
            # Query distinct users per day
            stmt = select(
                func.date(Message.created_at).label("date"),
                func.count(func.distinct(Message.user_id)).label("dau"),
            ).where(
                (Message.created_at >= start_date)
                & (Message.created_at <= end_date)
                & (Message.role == MessageRole.user)
            ).group_by(
                func.date(Message.created_at)
            ).order_by(
                func.date(Message.created_at)
            )

            results = await db.execute(stmt)
            data = []

            for date, dau in results:
                # Calculate MAU (active in last 30 days from this date)
                mau_date = date - timedelta(days=30)
                mau_stmt = select(
                    func.count(func.distinct(Message.user_id))
                ).where(
                    (Message.created_at >= mau_date)
                    & (Message.created_at <= date)
                    & (Message.role == MessageRole.user)
                )
                mau = await db.scalar(mau_stmt) or 0

                data.append({
                    "date": date.isoformat(),
                    "dau": dau,
                    "mau": mau,
                })

            return data

        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            return []

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """
        Get message volume per day.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of daily message counts
        """
        try:
            stmt = select(
                func.date(Message.created_at).label("date"),
                func.count(Message.id).label("messages"),
            ).where(
                (Message.created_at >= start_date)
                & (Message.created_at <= end_date)
                & (Message.role == MessageRole.user)
            ).group_by(
                func.date(Message.created_at)
            ).order_by(
                func.date(Message.created_at)
            )

            results = await db.execute(stmt)
            return [
                {"date": date.isoformat(), "messages": count}
                for date, count in results
            ]

        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    @staticmethod
    async def get_tokens(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """
        Get token usage per day.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of daily token usage
        """
        try:
            stmt = select(
                func.date(ModelRequestLog.created_at).label("date"),
                func.sum(ModelRequestLog.input_tokens).label("input_tokens"),
                func.sum(ModelRequestLog.output_tokens).label("output_tokens"),
            ).where(
                (ModelRequestLog.created_at >= start_date)
                & (ModelRequestLog.created_at <= end_date)
                & (ModelRequestLog.status == "success")
            ).group_by(
                func.date(ModelRequestLog.created_at)
            ).order_by(
                func.date(ModelRequestLog.created_at)
            )

            results = await db.execute(stmt)
            return [
                {
                    "date": date.isoformat(),
                    "input_tokens": input_tokens or 0,
                    "output_tokens": output_tokens or 0,
                    "total_tokens": (input_tokens or 0) + (output_tokens or 0),
                }
                for date, input_tokens, output_tokens in results
            ]

        except Exception as e:
            logger.error(f"Failed to get tokens: {e}")
            return []

    @staticmethod
    async def get_cost(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """
        Get estimated cost per day.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dict with daily costs and total
        """
        try:
            stmt = select(
                func.date(ModelRequestLog.created_at).label("date"),
                func.sum(ModelRequestLog.estimated_cost).label("cost"),
            ).where(
                (ModelRequestLog.created_at >= start_date)
                & (ModelRequestLog.created_at <= end_date)
                & (ModelRequestLog.status == "success")
            ).group_by(
                func.date(ModelRequestLog.created_at)
            ).order_by(
                func.date(ModelRequestLog.created_at)
            )

            results = await db.execute(stmt)
            data = []
            total_cost = 0

            for date, cost in results:
                cost_float = float(cost) if cost else 0
                total_cost += cost_float
                data.append({
                    "date": date.isoformat(),
                    "cost": cost_float,
                })

            return {
                "data": data,
                "total_cost": total_cost,
            }

        except Exception as e:
            logger.error(f"Failed to get cost: {e}")
            return {"data": [], "total_cost": 0}

    @staticmethod
    async def get_plan_distribution(db: AsyncSession) -> list[dict]:
        """
        Get subscription plan distribution.

        Args:
            db: Database session

        Returns:
            List of plan distribution data
        """
        try:
            stmt = select(
                Subscription.plan,
                func.count(Subscription.id).label("count"),
            ).where(
                Subscription.status == SubscriptionStatus.active
            ).group_by(
                Subscription.plan
            )

            results = await db.execute(stmt)

            # Get total for percentage calculation
            total_stmt = select(func.count(Subscription.id)).where(
                Subscription.status == SubscriptionStatus.active
            )
            total = await db.scalar(total_stmt) or 1

            data = []
            for plan, count in results:
                percentage = (count / total * 100) if total > 0 else 0
                data.append({
                    "plan": plan.value,
                    "users": count,
                    "percentage": round(percentage, 1),
                })

            return data

        except Exception as e:
            logger.error(f"Failed to get plan distribution: {e}")
            return []

    @staticmethod
    async def _calculate_monthly_churn(db: AsyncSession) -> float:
        """
        Calculate monthly churn rate.

        Churn = (cancelled paid subscriptions in month) / (paid subscriptions at start)

        Args:
            db: Database session

        Returns:
            Churn rate as percentage (0-100)
        """
        try:
            # Simplified: current cancelled count / current paid count
            # A full implementation would track historical data

            cancelled_stmt = select(func.count(Subscription.id)).where(
                (Subscription.plan.in_([SubscriptionPlan.plus, SubscriptionPlan.pro]))
                & (Subscription.status == SubscriptionStatus.canceled)
            )
            cancelled = await db.scalar(cancelled_stmt) or 1

            paid_stmt = select(func.count(Subscription.id)).where(
                Subscription.plan.in_([SubscriptionPlan.plus, SubscriptionPlan.pro])
            )
            paid = await db.scalar(paid_stmt) or 1

            churn_rate = (cancelled / paid * 100) if paid > 0 else 0
            return round(churn_rate, 1)

        except Exception as e:
            logger.error(f"Failed to calculate churn: {e}")
            return 0

    @staticmethod
    async def get_retention(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """
        Get retention cohorts (simplified weekly).

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of retention cohort data
        """
        try:
            # Simplified retention: users who signed up each week
            # and how many are still active in following weeks

            cohorts = []
            current_date = start_date

            while current_date <= end_date:
                cohort_end = current_date + timedelta(weeks=1)

                # Users who signed up in this week
                cohort_users_stmt = select(func.count(User.id)).where(
                    (User.created_at >= current_date)
                    & (User.created_at < cohort_end)
                )
                cohort_size = await db.scalar(cohort_users_stmt) or 0

                if cohort_size == 0:
                    current_date = cohort_end
                    continue

                # Track retention over 4 weeks
                retention_data = {
                    "cohort": current_date.strftime("%Y-%m-%d"),
                    "users": cohort_size,
                }

                for week in range(4):
                    week_start = current_date + timedelta(weeks=week)
                    week_end = week_start + timedelta(weeks=1)

                    # Active users from this cohort in this week
                    active_stmt = select(
                        func.count(func.distinct(Message.user_id))
                    ).where(
                        (Message.user_id.in_(
                            select(User.id).where(
                                (User.created_at >= current_date)
                                & (User.created_at < cohort_end)
                            )
                        ))
                        & (Message.created_at >= week_start)
                        & (Message.created_at < week_end)
                    )
                    active = await db.scalar(active_stmt) or 0
                    retention_data[f"week_{week}"] = active

                cohorts.append(retention_data)
                current_date = cohort_end

            return cohorts

        except Exception as e:
            logger.error(f"Failed to get retention: {e}")
            return []

    @staticmethod
    async def get_model_performance(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """
        Get model performance statistics.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of model performance data
        """
        try:
            stmt = select(
                ModelRequestLog.model,
                func.count(ModelRequestLog.id).label("requests"),
                func.sum(
                    func.cast(
                        ModelRequestLog.status == "success",
                        func.Integer,
                    )
                ).label("successes"),
                func.avg(ModelRequestLog.latency_ms).label("avg_latency"),
                func.sum(ModelRequestLog.input_tokens).label("input_tokens"),
                func.sum(ModelRequestLog.output_tokens).label("output_tokens"),
                func.sum(ModelRequestLog.estimated_cost).label("cost"),
            ).where(
                (ModelRequestLog.created_at >= start_date)
                & (ModelRequestLog.created_at <= end_date)
            ).group_by(
                ModelRequestLog.model
            )

            results = await db.execute(stmt)
            data = []

            for (
                model,
                requests,
                successes,
                avg_latency,
                input_tokens,
                output_tokens,
                cost,
            ) in results:
                success_rate = (
                    (successes / requests * 100) if requests > 0 else 0
                )
                error_rate = 100 - success_rate

                data.append({
                    "model": model,
                    "requests": requests,
                    "success_rate": round(success_rate, 1),
                    "error_rate": round(error_rate, 1),
                    "avg_latency_ms": round(avg_latency, 0) if avg_latency else 0,
                    "p50_latency_ms": 0,  # Would need percentile query
                    "p95_latency_ms": 0,
                    "p99_latency_ms": 0,
                    "input_tokens": input_tokens or 0,
                    "output_tokens": output_tokens or 0,
                    "total_tokens": (input_tokens or 0) + (output_tokens or 0),
                    "estimated_cost": float(cost) if cost else 0,
                })

            return data

        except Exception as e:
            logger.error(f"Failed to get model performance: {e}")
            return []


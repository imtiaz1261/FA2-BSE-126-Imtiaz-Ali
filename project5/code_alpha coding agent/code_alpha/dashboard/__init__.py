"""
Web Dashboard Backend for Code Alpha

Serves real-time agent status, task metrics, and memory insights to web UI.
"""

from .models import (
    DashboardState,
    TaskMetrics,
    MemoryStats,
    DashboardConfig,
    ActivityLog,
    DashboardMetric,
    MetricType,
)
from .routes import setup_dashboard_routes
from .service import DashboardService

__all__ = [
    'DashboardState',
    'TaskMetrics',
    'MemoryStats',
    'DashboardConfig',
    'ActivityLog',
    'DashboardMetric',
    'MetricType',
    'setup_dashboard_routes',
    'DashboardService',
]

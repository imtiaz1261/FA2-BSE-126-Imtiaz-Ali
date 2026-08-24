"""
Dashboard service for aggregating and serving dashboard data.

Collects metrics from various sources and provides unified API.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from .models import DashboardState, TaskMetrics, MemoryStats, DashboardMetric, DashboardConfig

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics from agent execution."""
    
    def __init__(self):
        self.task_metrics: Dict[str, TaskMetrics] = {}
        self.metric_history: List[DashboardMetric] = []
    
    def record_task_metrics(self, metrics: TaskMetrics) -> None:
        """Record metrics for a task."""
        self.task_metrics[metrics.task_id] = metrics
        logger.debug(f"Recorded metrics for task {metrics.task_id}")
    
    def get_task_metrics(self, task_id: str) -> Optional[TaskMetrics]:
        """Get metrics for a task."""
        return self.task_metrics.get(task_id)
    
    def record_metric(self, metric: DashboardMetric) -> None:
        """Record a single metric."""
        self.metric_history.append(metric)
        
        # Keep last 1000 metric points
        if len(self.metric_history) > 1000:
            self.metric_history = self.metric_history[-1000:]


class DashboardService:
    """
    Service for managing dashboard state and providing data to UI.
    
    Aggregates metrics, memory stats, and activity logs.
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        self.config = config or DashboardConfig()
        self.state = DashboardState()
        self.metrics_collector = MetricsCollector()
        self.start_time = datetime.utcnow()
    
    def set_agent_status(self, status: str) -> None:
        """Update agent status."""
        self.state.agent_status = status
        logger.debug(f"Agent status: {status}")
    
    def set_current_task(self, task_id: str, progress: int = 0) -> None:
        """Set current running task."""
        self.state.current_task = task_id
        self.state.current_task_progress = progress
    
    def update_task_progress(self, progress: int) -> None:
        """Update progress of current task."""
        self.state.current_task_progress = progress
    
    def record_task_completion(self, metrics: TaskMetrics) -> None:
        """Record task completion with metrics."""
        self.metrics_collector.record_task_metrics(metrics)
        self.state.add_task_metrics(metrics)
        
        # Log activity
        self.state.add_activity(
            event_type="task_complete",
            task_id=metrics.task_id,
            message=f"Task completed: {metrics.phase} phase",
            data={
                "progress": metrics.progress,
                "tests_passed": metrics.tests_passed,
                "tests_failed": metrics.tests_failed,
                "files_modified": metrics.files_modified,
            }
        )
    
    def record_error_fixed(self, task_id: str, error_msg: str) -> None:
        """Record error that was fixed."""
        self.state.add_activity(
            event_type="error_fixed",
            task_id=task_id,
            message=f"Fixed error: {error_msg}",
        )
    
    def update_memory_stats(self, stats: MemoryStats) -> None:
        """Update memory statistics."""
        self.state.memory_stats = stats
        logger.debug(f"Memory stats updated: {stats.total_entries} entries")
    
    def add_metric(self, name: str, value: float, unit: str = "") -> None:
        """Add a metric data point."""
        metric = DashboardMetric(name=name, value=value, unit=unit)
        self.state.metrics.append(metric)
        self.metrics_collector.record_metric(metric)
    
    def get_state(self) -> DashboardState:
        """Get current dashboard state."""
        # Update uptime
        uptime = datetime.utcnow() - self.start_time
        self.state.uptime_seconds = int(uptime.total_seconds())
        
        return self.state
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Get dashboard state as dictionary."""
        return self.get_state().to_dict()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        state = self.get_state()
        
        # Calculate averages
        if state.total_tests_passed + state.total_tests_failed > 0:
            test_success_rate = (
                state.total_tests_passed /
                (state.total_tests_passed + state.total_tests_failed)
            ) * 100
        else:
            test_success_rate = 0.0
        
        if state.total_errors_fixed > 0 and len(state.recent_tasks) > 0:
            avg_fix_rate = sum(
                t.fix_rate() for t in state.recent_tasks if t.errors_encountered > 0
            ) / len(state.recent_tasks)
        else:
            avg_fix_rate = 0.0
        
        return {
            "agent_status": state.agent_status,
            "tasks_completed": state.tasks_completed,
            "total_tests_passed": state.total_tests_passed,
            "total_tests_failed": state.total_tests_failed,
            "test_success_rate": test_success_rate,
            "total_errors_fixed": state.total_errors_fixed,
            "avg_error_fix_rate": avg_fix_rate,
            "total_files_modified": state.total_files_modified,
            "uptime_seconds": state.uptime_seconds,
            "memory_entries": (
                state.memory_stats.total_entries
                if state.memory_stats else 0
            ),
        }
    
    def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent activity log entries."""
        entries = self.state.activity_log[-limit:]
        return [e.to_dict() for e in reversed(entries)]
    
    def get_top_metrics(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing metric values."""
        # Group metrics by name and get latest value
        latest_metrics = {}
        for metric in self.metrics_collector.metric_history:
            latest_metrics[metric.name] = metric.value
        
        # Sort by value and return top
        sorted_metrics = sorted(latest_metrics.items(), key=lambda x: x[1], reverse=True)
        return [
            {"name": name, "value": value}
            for name, value in sorted_metrics[:limit]
        ]
    
    def get_performance_over_time(
        self,
        metric_name: str,
        minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Get metric values over time period.
        
        Args:
            metric_name: Name of metric to retrieve
            minutes: Time window in minutes
        
        Returns:
            List of {timestamp, value} dicts
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        result = []
        for metric in self.metrics_collector.metric_history:
            metric_time = datetime.fromisoformat(metric.timestamp)
            if metric_time >= cutoff_time and metric.name == metric_name:
                result.append({
                    "timestamp": metric.timestamp,
                    "value": metric.value,
                })
        
        return result
    
    def reset_stats(self) -> None:
        """Reset dashboard statistics (for new session)."""
        self.state = DashboardState()
        self.metrics_collector = MetricsCollector()
        self.start_time = datetime.utcnow()
        logger.info("Dashboard statistics reset")


class RealTimeUpdater:
    """
    Provides real-time updates via streaming/WebSocket.
    
    Notifies connected clients of dashboard changes.
    """
    
    def __init__(self, dashboard: DashboardService):
        self.dashboard = dashboard
        self.subscribers: List[Any] = []  # WebSocket connections
    
    def subscribe(self, websocket: Any) -> None:
        """Subscribe to updates."""
        self.subscribers.append(websocket)
        logger.debug(f"Subscribed to updates. Subscribers: {len(self.subscribers)}")
    
    def unsubscribe(self, websocket: Any) -> None:
        """Unsubscribe from updates."""
        self.subscribers.remove(websocket)
        logger.debug(f"Unsubscribed from updates. Subscribers: {len(self.subscribers)}")
    
    async def broadcast_update(self, data: Dict[str, Any]) -> None:
        """Broadcast update to all subscribers."""
        import json
        
        msg = json.dumps({
            "type": "dashboard_update",
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        disconnected = []
        for subscriber in self.subscribers:
            try:
                await subscriber.send_text(msg)
            except Exception as e:
                logger.warning(f"Error sending update: {e}")
                disconnected.append(subscriber)
        
        # Remove disconnected clients
        for ws in disconnected:
            self.unsubscribe(ws)
    
    async def broadcast_state_update(self) -> None:
        """Broadcast full dashboard state."""
        state = self.dashboard.get_state_dict()
        await self.broadcast_update(state)
    
    async def broadcast_metric(self, name: str, value: float, unit: str = "") -> None:
        """Broadcast new metric."""
        self.dashboard.add_metric(name, value, unit)
        
        await self.broadcast_update({
            "type": "metric",
            "name": name,
            "value": value,
            "unit": unit,
        })

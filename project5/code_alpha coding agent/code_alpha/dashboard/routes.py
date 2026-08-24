"""
FastAPI routes for dashboard backend.

Provides REST endpoints for web UI to fetch dashboard data.
"""

import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query

from .models import DashboardConfig
from .service import DashboardService, RealTimeUpdater

logger = logging.getLogger(__name__)


def setup_dashboard_routes(
    app: FastAPI,
    dashboard_service: Optional[DashboardService] = None,
) -> DashboardService:
    """
    Setup dashboard routes on FastAPI app.
    
    Args:
        app: FastAPI application
        dashboard_service: Optional existing service (creates new if None)
    
    Returns:
        DashboardService instance
    """
    # Create or use provided service
    service = dashboard_service or DashboardService()
    updater = RealTimeUpdater(service)
    
    # ========================================================================
    # Dashboard State Endpoints
    # ========================================================================
    
    @app.get("/dashboard")
    async def get_dashboard():
        """Get complete dashboard state."""
        return service.get_state_dict()
    
    @app.get("/dashboard/summary")
    async def get_dashboard_summary():
        """Get dashboard summary statistics."""
        return service.get_summary()
    
    @app.get("/dashboard/status")
    async def get_agent_status():
        """Get current agent status."""
        state = service.get_state()
        return {
            "status": state.agent_status,
            "current_task": state.current_task,
            "current_task_progress": state.current_task_progress,
            "uptime_seconds": state.uptime_seconds,
        }
    
    # ========================================================================
    # Metrics Endpoints
    # ========================================================================
    
    @app.get("/dashboard/metrics")
    async def get_metrics():
        """Get all recorded metrics."""
        state = service.get_state()
        return {
            "metrics": [m.to_dict() for m in state.metrics],
            "count": len(state.metrics),
        }
    
    @app.get("/dashboard/metrics/summary")
    async def get_metrics_summary():
        """Get summary of top metrics."""
        return {"top_metrics": service.get_top_metrics(limit=10)}
    
    @app.get("/dashboard/metrics/{metric_name}")
    async def get_metric_history(
        metric_name: str,
        minutes: int = Query(60, ge=1, le=1440)
    ):
        """
        Get metric values over time.
        
        Args:
            metric_name: Name of metric to retrieve
            minutes: Time window in minutes (1-1440)
        
        Returns:
            List of metric data points with timestamps
        """
        return {
            "metric": metric_name,
            "period_minutes": minutes,
            "data": service.get_performance_over_time(metric_name, minutes),
        }
    
    # ========================================================================
    # Activity Log Endpoints
    # ========================================================================
    
    @app.get("/dashboard/activity")
    async def get_activity_log(limit: int = Query(20, ge=1, le=100)):
        """Get recent activity log entries."""
        return {
            "entries": service.get_recent_activity(limit),
            "count": len(service.get_recent_activity(limit)),
        }
    
    # ========================================================================
    # Task Metrics Endpoints
    # ========================================================================
    
    @app.get("/dashboard/tasks")
    async def get_recent_tasks():
        """Get recent tasks with metrics."""
        state = service.get_state()
        return {
            "tasks": [t.to_dict() for t in state.recent_tasks],
            "count": len(state.recent_tasks),
        }
    
    @app.get("/dashboard/tasks/{task_id}")
    async def get_task_metrics(task_id: str):
        """Get metrics for specific task."""
        metrics = service.metrics_collector.get_task_metrics(task_id)
        if not metrics:
            return {"error": f"No metrics found for task {task_id}"}
        return metrics.to_dict()
    
    # ========================================================================
    # Memory Statistics Endpoints
    # ========================================================================
    
    @app.get("/dashboard/memory")
    async def get_memory_stats():
        """Get project memory statistics."""
        state = service.get_state()
        if not state.memory_stats:
            return {"message": "No memory statistics available"}
        return state.memory_stats.to_dict()
    
    # ========================================================================
    # Real-Time WebSocket Endpoint
    # ========================================================================
    
    @app.websocket("/ws/dashboard")
    async def websocket_dashboard(websocket: WebSocket):
        """
        WebSocket endpoint for real-time dashboard updates.
        
        Sends full state updates at regular intervals.
        """
        await websocket.accept()
        updater.subscribe(websocket)
        
        try:
            # Send initial state
            await updater.broadcast_state_update()
            
            # Keep connection alive
            while True:
                # Receive heartbeat or control messages
                data = await websocket.receive_text()
                
                # Echo pong to keep connection alive
                await updater.broadcast_update({
                    "type": "pong",
                    "message": "Connection active",
                })
        
        except WebSocketDisconnect:
            updater.unsubscribe(websocket)
            logger.info("Dashboard WebSocket client disconnected")
        except Exception as e:
            logger.error(f"Dashboard WebSocket error: {e}")
            updater.unsubscribe(websocket)
    
    # ========================================================================
    # Control Endpoints
    # ========================================================================
    
    @app.post("/dashboard/reset")
    async def reset_dashboard():
        """Reset all dashboard statistics."""
        service.reset_stats()
        return {"status": "success", "message": "Dashboard reset"}
    
    @app.post("/dashboard/status/{status}")
    async def set_agent_status(status: str):
        """Set agent status."""
        service.set_agent_status(status)
        await updater.broadcast_state_update()
        return {"status": status}
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    @app.get("/dashboard/health")
    async def dashboard_health():
        """Check dashboard service health."""
        return {
            "status": "healthy",
            "service": "dashboard",
            "real_time_subscribers": len(updater.subscribers),
        }
    
    return service

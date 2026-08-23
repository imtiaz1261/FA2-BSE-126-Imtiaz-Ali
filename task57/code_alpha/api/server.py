"""
FastAPI server for Code Alpha agent.

Provides REST endpoints for task management, execution control, and status monitoring.
Supports real-time streaming via Server-Sent Events (SSE).
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, AsyncGenerator
import os

from fastapi import FastAPI, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from code_alpha.api.schemas import (
    TaskRunRequest, TaskRunResponse, TaskStatusResponse, TaskListResponse,
    TaskApprovalRequest, TaskResultSummary, SpecGenerationRequest, SpecGenerationResponse,
    PlanGenerationRequest, PlanGenerationResponse, ImplementationRequest, ImplementationResponse,
    TestRequest, TestResponse, HealthCheckResponse, ErrorResponse, DetailedTaskStatus
)
from code_alpha.api.task_manager import TaskManager, TaskStatus, Task
from code_alpha.orchestration.orchestrator import Orchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Code Alpha API",
    description="REST API for autonomous code generation agent",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
task_manager = TaskManager()
app_start_time = datetime.utcnow()


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Check API health and status"""
    uptime = (datetime.utcnow() - app_start_time).total_seconds()
    summary = task_manager.get_summary()
    
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        uptime_seconds=uptime,
        active_tasks=summary["running"],
        completed_tasks=summary["completed"],
        api_url="http://localhost:8000"
    )


@app.get("/status")
async def server_status():
    """Get detailed server status"""
    summary = task_manager.get_summary()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - app_start_time).total_seconds(),
        "tasks": summary,
        "api_version": "0.1.0"
    }


# ============================================================================
# Task Management Endpoints
# ============================================================================

@app.post("/tasks", response_model=TaskRunResponse, status_code=201)
async def create_task(
    request: TaskRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Create and enqueue a new task.
    
    Triggers the full pipeline: spec generation → planning → implementation → testing
    
    Returns task ID for status polling or SSE subscription.
    """
    try:
        # Create task
        task = task_manager.create_task(
            prompt=request.prompt,
            repo_path=request.repo_path or ".",
            auto_approve_low_risk=request.auto_approve_low_risk,
            max_retries=request.max_retries,
            timeout_seconds=request.timeout_seconds,
            on_failure=request.on_failure,
            tags=request.tags,
            metadata=request.metadata
        )
        
        # Start orchestrator in background
        background_tasks.add_task(
            orchestrator.run_task,
            task,
            task_manager
        )
        
        return TaskRunResponse(
            task_id=task.task_id,
            status=task.status.value,
            created_at=task.created_at,
            message="Task created and queued for execution"
        )
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str = Path(..., description="Task ID")
):
    """
    Get current status of a task.
    
    Returns comprehensive task information including progress, logs, edits, and results.
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        progress=task.progress,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        duration_seconds=task.duration_seconds,
        prompt=task.prompt,
        repo_path=task.repo_path,
        logs=[
            {"timestamp": entry["timestamp"], "level": entry["level"], "message": entry["message"]}
            for entry in task.logs
        ],
        edits=[
            {
                "file_path": edit["file_path"],
                "operation": edit["operation"],
                "lines_changed": edit["lines_changed"],
                "description": edit["description"]
            }
            for edit in task.edits
        ],
        test_results=[
            {
                "test_name": result["test_name"],
                "status": result["status"],
                "duration_seconds": result["duration_seconds"],
                "output": result["output"],
                "error_message": result.get("error_message")
            }
            for result in task.test_results
        ],
        error=task.error,
        error_type=task.error_type,
        tags=task.tags,
        metadata=task.metadata,
        current_operation=task.current_operation,
        current_file=task.current_file
    )


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List all tasks with optional filtering.
    
    Supports filtering by status and tags. Useful for dashboards and monitoring.
    """
    try:
        status_enum = TaskStatus(status) if status else None
        tasks, total = task_manager.get_tasks(
            status=status_enum,
            limit=limit,
            offset=offset,
            tags=tags
        )
        
        return TaskListResponse(
            tasks=[
                TaskStatusResponse(
                    task_id=t.task_id,
                    status=t.status.value,
                    progress=t.progress,
                    created_at=t.created_at,
                    started_at=t.started_at,
                    completed_at=t.completed_at,
                    duration_seconds=t.duration_seconds,
                    prompt=t.prompt,
                    repo_path=t.repo_path,
                    tags=t.tags,
                    error=t.error
                )
                for t in tasks
            ],
            total=total,
            limit=limit,
            offset=offset
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks/{task_id}/logs", response_model=List[dict])
async def get_task_logs(
    task_id: str = Path(..., description="Task ID"),
    level: Optional[str] = Query(None, description="Filter by log level")
):
    """Get task execution logs"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    logs = task.logs
    if level:
        logs = [log for log in logs if log["level"] == level]
    
    return logs


@app.get("/tasks/{task_id}/stream")
async def stream_task_logs(
    task_id: str = Path(..., description="Task ID")
):
    """
    Stream task logs in real-time using Server-Sent Events (SSE).
    
    Useful for web UIs, CI logs, or real-time monitoring.
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for task progress"""
        last_log_index = 0
        
        while True:
            # Send new logs
            if last_log_index < len(task.logs):
                new_logs = task.logs[last_log_index:]
                for log in new_logs:
                    yield f"data: {{'type': 'log', 'data': {log}}}\n\n"
                last_log_index = len(task.logs)
            
            # Send status update
            yield f"data: {{'type': 'status', 'status': '{task.status.value}', 'progress': {task.progress}}}\n\n"
            
            # Check if task is complete
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                yield f"data: {{'type': 'complete', 'status': '{task.status.value}'}}\n\n"
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Task Review & Approval Endpoints
# ============================================================================

@app.post("/tasks/{task_id}/approve", response_model=dict)
async def approve_changes(
    task_id: str = Path(..., description="Task ID"),
    request: TaskApprovalRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Approve pending changes for a task.
    
    Resumes task execution after human review.
    """
    try:
        task_manager.approve_changes(task_id, request.comment if request else None)
        
        # Resume orchestrator
        background_tasks.add_task(orchestrator.resume_task, task_id, task_manager)
        
        return {"status": "approved", "task_id": task_id, "message": "Changes approved"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tasks/{task_id}/reject", response_model=dict)
async def reject_changes(
    task_id: str = Path(..., description="Task ID"),
    request: TaskApprovalRequest = None
):
    """Reject pending changes for a task"""
    try:
        reason = request.comment if request else "Rejected by user"
        task_manager.reject_changes(task_id, reason)
        
        return {"status": "rejected", "task_id": task_id, "message": "Changes rejected"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tasks/{task_id}/request-changes", response_model=dict)
async def request_changes(
    task_id: str = Path(..., description="Task ID"),
    request: TaskApprovalRequest = None,
    background_tasks: BackgroundTasks = None
):
    """Request modifications to pending changes"""
    try:
        task_manager.request_approval(
            task_id,
            {"feedback": request.comment} if request else {}
        )
        
        # Trigger re-implementation
        background_tasks.add_task(orchestrator.refactor_task, task_id, task_manager)
        
        return {
            "status": "changes_requested",
            "task_id": task_id,
            "message": "Requested changes queued"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Pipeline Stage Endpoints
# ============================================================================

@app.post("/tasks/spec", response_model=SpecGenerationResponse)
async def generate_spec(request: SpecGenerationRequest):
    """Generate specification documents"""
    try:
        task = task_manager.create_task(
            prompt=request.prompt,
            repo_path=request.repo_path or ".",
            tags=["spec-only"]
        )
        
        # Run spec generation stage only
        result = await orchestrator.generate_specs(
            task.task_id,
            request.prompt,
            request.repo_path or "."
        )
        
        return SpecGenerationResponse(
            task_id=task.task_id,
            requirements=result.get("requirements", ""),
            design=result.get("design") if request.include_design else None,
            tasks=result.get("tasks") if request.include_tasks else None,
            estimated_duration_minutes=result.get("estimated_minutes", 30)
        )
    
    except Exception as e:
        logger.error(f"Error generating spec: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tasks/plan", response_model=PlanGenerationResponse)
async def generate_plan(request: PlanGenerationRequest):
    """Generate implementation plan"""
    try:
        task = task_manager.create_task(
            prompt=f"Requirements: {request.requirements}\n\nDesign: {request.design}",
            repo_path=request.repo_path or ".",
            tags=["plan-only"]
        )
        
        # Run plan generation stage
        result = await orchestrator.generate_plan(
            task.task_id,
            request.requirements,
            request.design,
            request.repo_path or "."
        )
        
        return PlanGenerationResponse(
            task_id=task.task_id,
            tasks=result.get("tasks", []),
            dependencies=result.get("dependencies", []),
            estimated_duration_hours=result.get("estimated_hours", 4)
        )
    
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tasks/implement", response_model=ImplementationResponse)
async def implement_changes(request: ImplementationRequest, background_tasks: BackgroundTasks):
    """Execute implementation"""
    try:
        task = task_manager.create_task(
            prompt=str(request.plan),
            repo_path=request.repo_path or ".",
            auto_approve_low_risk=request.auto_approve,
            tags=["implement-only"]
        )
        
        # Run implementation in background
        background_tasks.add_task(
            orchestrator.implement_plan,
            task.task_id,
            request.plan,
            request.repo_path or ".",
            task_manager
        )
        
        return ImplementationResponse(
            task_id=task.task_id,
            status="started",
            files_changed=[],
            total_lines_changed=0
        )
    
    except Exception as e:
        logger.error(f"Error implementing changes: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tasks/test", response_model=TestResponse)
async def run_tests(request: TestRequest):
    """Run test suite"""
    try:
        task = task_manager.create_task(
            prompt="Run tests",
            repo_path=request.repo_path or ".",
            tags=["test-only"]
        )
        
        # Run tests
        result = await orchestrator.run_tests(
            task.task_id,
            request.repo_path or ".",
            request.test_filter,
            request.coverage,
            task_manager
        )
        
        return TestResponse(
            task_id=task.task_id,
            total_tests=result.get("total", 0),
            passed_tests=result.get("passed", 0),
            failed_tests=result.get("failed", 0),
            skipped_tests=result.get("skipped", 0),
            duration_seconds=result.get("duration", 0),
            coverage_percentage=result.get("coverage"),
            test_output=result.get("output", "")
        )
    
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Task Control Endpoints
# ============================================================================

@app.post("/tasks/{task_id}/pause", response_model=dict)
async def pause_task(task_id: str = Path(...)):
    """Pause a running task"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task_manager.update_task_status(task_id, TaskStatus.AWAITING_APPROVAL)
        
        return {"status": "paused", "task_id": task_id}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tasks/{task_id}/cancel", response_model=dict)
async def cancel_task(task_id: str = Path(...)):
    """Cancel a running task"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task_manager.update_task_status(task_id, TaskStatus.CANCELLED)
        
        return {"status": "cancelled", "task_id": task_id}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tasks/{task_id}/retry", response_model=dict)
async def retry_task(task_id: str = Path(...), background_tasks: BackgroundTasks = None):
    """Retry a failed task"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task_manager.update_task_status(task_id, TaskStatus.PENDING)
        
        # Restart orchestrator
        background_tasks.add_task(orchestrator.run_task, task, task_manager)
        
        return {"status": "retrying", "task_id": task_id, "message": "Task queued for retry"}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/tasks/{task_id}", response_model=dict)
async def delete_task(task_id: str = Path(...)):
    """Delete a task"""
    try:
        task_manager.delete_task(task_id)
        return {"status": "deleted", "task_id": task_id}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on server startup"""
    logger.info("Code Alpha API starting up...")
    logger.info(f"Task manager initialized with {len(task_manager.tasks)} persisted tasks")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("Code Alpha API shutting down...")


# ============================================================================
# Root endpoint
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Code Alpha API",
        "version": "0.1.0",
        "docs": "/api/docs",
        "status": "/health"
    }


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Start the API server"""
    uvicorn.run(
        "code_alpha.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()

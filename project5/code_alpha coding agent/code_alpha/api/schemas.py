"""
Pydantic schemas for API requests and responses.

Defines the complete data models for the REST API including task management,
status tracking, and machine-readable output formats.
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


class TaskState(str):
    """Task execution states"""
    PENDING = "pending"
    RUNNING = "running"
    PLANNING = "planning"
    GENERATING = "generating"
    TESTING = "testing"
    FIXING = "fixing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRunRequest(BaseModel):
    """Request to create a new task run"""
    
    prompt: str = Field(
        ...,
        description="Task description or specification",
        min_length=1,
        max_length=10000
    )
    repo_path: Optional[str] = Field(
        None,
        description="Path to repository (defaults to current directory)"
    )
    auto_approve_low_risk: bool = Field(
        False,
        description="Automatically approve low-risk changes without review"
    )
    max_retries: int = Field(
        3,
        description="Maximum number of retry attempts",
        ge=0,
        le=10
    )
    timeout_seconds: int = Field(
        3600,
        description="Task timeout in seconds",
        ge=60,
        le=86400
    )
    on_failure: Literal["stop", "ask", "auto-fix"] = Field(
        "ask",
        description="What to do on test failure"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing tasks"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata"
    )

    @validator('prompt')
    def prompt_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v.strip()


class TaskRunResponse(BaseModel):
    """Response for task creation"""
    
    task_id: str = Field(
        ...,
        description="Unique task identifier"
    )
    status: str = Field(
        TaskState.PENDING,
        description="Initial task status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Task creation timestamp"
    )
    message: str = Field(
        "Task created successfully",
        description="Status message"
    )


class TaskLogEntry(BaseModel):
    """A single log entry from task execution"""
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow
    )
    level: Literal["debug", "info", "warning", "error"] = "info"
    message: str
    context: Optional[Dict[str, Any]] = None


class TaskEditSummary(BaseModel):
    """Summary of code changes in a task"""
    
    file_path: str
    operation: Literal["create", "modify", "delete"]
    lines_changed: int
    description: str


class TaskTestResult(BaseModel):
    """Test execution result"""
    
    test_name: str
    status: Literal["passed", "failed", "skipped"]
    duration_seconds: float
    output: str
    error_message: Optional[str] = None


class TaskApprovalRequest(BaseModel):
    """Request to approve or reject changes"""
    
    action: Literal["approve", "reject", "request_changes"]
    comment: Optional[str] = Field(
        None,
        description="Optional comment or feedback"
    )


class TaskStatusResponse(BaseModel):
    """Current status of a task"""
    
    task_id: str
    status: str = Field(
        description="Current task state"
    )
    progress: int = Field(
        0,
        description="Progress percentage (0-100)",
        ge=0,
        le=100
    )
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Task details
    prompt: str
    repo_path: str
    
    # Results
    logs: List[TaskLogEntry] = Field(default_factory=list)
    edits: List[TaskEditSummary] = Field(default_factory=list)
    test_results: List[TaskTestResult] = Field(default_factory=list)
    
    # Error information
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Current operation
    current_operation: Optional[str] = None
    current_file: Optional[str] = None


class TaskListResponse(BaseModel):
    """List of tasks"""
    
    tasks: List[TaskStatusResponse]
    total: int
    limit: int
    offset: int


class TaskResultSummary(BaseModel):
    """Final result summary of a completed task (machine-readable)"""
    
    task_id: str
    status: str
    duration_seconds: float
    
    # Execution summary
    specs_generated: bool
    plan_created: bool
    code_generated: bool
    tests_passed: bool
    all_approved: bool
    
    # Metrics
    total_edits: int
    total_lines_changed: int
    total_tests: int
    passing_tests: int
    failing_tests: int
    coverage_delta: Optional[float] = None
    
    # File changes
    files_created: int
    files_modified: int
    files_deleted: int
    
    # Results
    pr_created: bool = False
    pr_url: Optional[str] = None
    
    # Logs and artifacts
    spec_path: Optional[str] = None
    plan_path: Optional[str] = None
    log_path: Optional[str] = None
    
    # Errors
    error_message: Optional[str] = None
    error_trace: Optional[str] = None
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


class SpecGenerationRequest(BaseModel):
    """Request to generate specifications"""
    
    prompt: str = Field(
        ...,
        description="Project description/requirements",
        min_length=1
    )
    repo_path: Optional[str] = None
    include_design: bool = Field(True, description="Generate design document")
    include_tasks: bool = Field(True, description="Break down into tasks")


class SpecGenerationResponse(BaseModel):
    """Result of specification generation"""
    
    task_id: str
    requirements: str
    design: Optional[str] = None
    tasks: Optional[List[str]] = None
    estimated_duration_minutes: int


class PlanGenerationRequest(BaseModel):
    """Request to generate implementation plan"""
    
    requirements: str = Field(..., description="Project requirements")
    design: str = Field(..., description="System design")
    repo_path: Optional[str] = None


class PlanGenerationResponse(BaseModel):
    """Implementation plan"""
    
    task_id: str
    tasks: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    estimated_duration_hours: float


class ImplementationRequest(BaseModel):
    """Request to implement changes"""
    
    plan: Dict[str, Any] = Field(..., description="Implementation plan")
    repo_path: Optional[str] = None
    auto_test: bool = Field(True, description="Run tests after implementation")
    auto_approve: bool = Field(False, description="Auto-approve low-risk changes")


class ImplementationResponse(BaseModel):
    """Implementation result"""
    
    task_id: str
    status: str
    files_changed: List[str]
    total_lines_changed: int
    tests_passed: bool = False
    test_count: int = 0
    issues: List[str] = Field(default_factory=list)


class TestRequest(BaseModel):
    """Request to run tests"""
    
    repo_path: Optional[str] = None
    test_filter: Optional[str] = None
    coverage: bool = Field(True, description="Include coverage report")


class TestResponse(BaseModel):
    """Test execution results"""
    
    task_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_seconds: float
    coverage_percentage: Optional[float] = None
    failed_tests_list: List[str] = Field(default_factory=list)
    test_output: str


class HealthCheckResponse(BaseModel):
    """API health status"""
    
    status: str
    version: str
    uptime_seconds: float
    active_tasks: int
    completed_tasks: int
    api_url: str


class ErrorResponse(BaseModel):
    """Error response"""
    
    error: str
    error_type: str
    status_code: int
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PipelineStage(BaseModel):
    """A stage in the execution pipeline"""
    
    stage_name: str
    status: str
    progress: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    message: str


class DetailedTaskStatus(BaseModel):
    """Detailed task status with pipeline stages"""
    
    task_id: str
    overall_status: str
    progress: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Pipeline stages
    stages: List[PipelineStage] = Field(default_factory=list)
    
    # Outputs
    requirements_spec: Optional[str] = None
    design_spec: Optional[str] = None
    implementation_plan: Optional[str] = None
    code_changes: List[Dict[str, Any]] = Field(default_factory=list)
    test_results: Optional[TestResponse] = None
    
    # Human review
    awaiting_approval: bool = False
    pending_changes: Optional[Dict[str, Any]] = None
    
    # Summary
    summary: Optional[TaskResultSummary] = None


class CIIntegrationConfig(BaseModel):
    """Configuration for CI/CD integration"""
    
    provider: Literal["github", "gitlab", "jenkins", "circleci", "generic"]
    auto_pr: bool = Field(True, description="Automatically create pull requests")
    auto_approve_low_risk: bool = False
    slack_webhook: Optional[str] = None
    email_on_completion: bool = False
    emails: List[str] = Field(default_factory=list)


class WebhookEvent(BaseModel):
    """Webhook event notification"""
    
    event_type: Literal["task_started", "task_progress", "task_completed", "task_failed", "approval_needed"]
    task_id: str
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)

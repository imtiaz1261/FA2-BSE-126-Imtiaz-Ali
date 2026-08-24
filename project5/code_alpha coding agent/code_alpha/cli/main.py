"""
Code Alpha Command-Line Interface (CLI).

Provides headless execution of the Code Alpha agent for CI/CD integration,
scripting, and automation workflows.

Usage:
    codealpha run "implement authentication module" --repo /path/to/repo
    codealpha spec --prompt "build todo app" --json
    codealpha plan --requirements spec.md --design design.md
    codealpha implement --plan plan.json --auto-approve
    codealpha test --repo /path/to/repo --coverage
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional
import logging

import typer
import rich
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.syntax import Syntax

from code_alpha.orchestration.orchestrator import Orchestrator
from code_alpha.api.task_manager import TaskManager, TaskStatus
from code_alpha.api.output_formatter import OutputFormatter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CLI app
app = typer.Typer(
    name="codealpha",
    help="Autonomous code generation agent - CLI interface",
    no_args_is_help=True,
    rich_markup_mode="rich"
)

console = Console()
formatter = OutputFormatter()
task_manager = TaskManager()


# ============================================================================
# Main "run" command - Full pipeline
# ============================================================================

@app.command(help="Run the complete pipeline (spec → plan → implement → test)")
def run(
    prompt: str = typer.Argument(
        ...,
        help="Task description or specification"
    ),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Path to repository (defaults to current directory)"
    ),
    auto_approve: bool = typer.Option(
        False,
        "--auto-approve-low-risk",
        "-a",
        help="Automatically approve low-risk changes"
    ),
    max_retries: int = typer.Option(
        3,
        "--max-retries",
        help="Maximum retry attempts on failure"
    ),
    timeout: int = typer.Option(
        3600,
        "--timeout",
        "-t",
        help="Task timeout in seconds"
    ),
    on_failure: str = typer.Option(
        "ask",
        "--on-failure",
        help="What to do on test failure: stop, ask, auto-fix"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output machine-readable JSON summary"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging"
    ),
    no_stream: bool = typer.Option(
        False,
        "--no-stream",
        help="Don't stream output (useful for CI)"
    )
):
    """
    Execute the complete Code Alpha pipeline.
    
    This command runs the full workflow:
    1. Generate specifications
    2. Create implementation plan
    3. Generate code
    4. Run tests
    5. Self-healing (fix failures)
    6. Final review
    
    Exit code: 0 on success, non-zero on failure (suitable for CI gating)
    """
    try:
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        repo_path = repo or "."
        
        # Create task
        task = task_manager.create_task(
            prompt=prompt,
            repo_path=repo_path,
            auto_approve_low_risk=auto_approve,
            max_retries=max_retries,
            timeout_seconds=timeout,
            on_failure=on_failure
        )
        
        console.print(f"\n[bold blue]🚀 Starting Code Alpha Run[/bold blue]")
        console.print(f"[dim]Task ID: {task.task_id}[/dim]")
        console.print(f"[dim]Repo: {repo_path}[/dim]\n")
        
        # Run orchestrator
        if no_stream:
            # Silent mode for CI
            result = orchestrator.run_task_sync(task, task_manager)
        else:
            # Stream output
            result = _run_with_progress(task, task_manager, orchestrator)
        
        # Handle results
        if result.get("success"):
            console.print(f"\n[bold green]✅ Task completed successfully![/bold green]")
            
            if json_output:
                _output_json_summary(task, result)
            else:
                _output_human_summary(task, result)
            
            sys.exit(0)
        
        else:
            console.print(f"\n[bold red]❌ Task failed[/bold red]")
            
            if json_output:
                _output_json_error(task, result)
            else:
                _output_human_error(task, result)
            
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        logger.exception(e)
        sys.exit(1)


def _run_with_progress(task, task_manager, orchestrator):
    """Run task with progress display"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        PercentageColumn(),
        console=console
    ) as progress:
        # Phases of execution
        phases = [
            ("Planning", 0, 20),
            ("Generating", 20, 50),
            ("Testing", 50, 80),
            ("Finalizing", 80, 100)
        ]
        
        progress_task = progress.add_task("[cyan]Executing...", total=100)
        
        # Run orchestrator
        result = orchestrator.run_task_sync(task, task_manager)
        
        # Update progress
        progress.update(progress_task, completed=100)
        
        return result


def _output_json_summary(task, result):
    """Output JSON summary for machine processing"""
    summary = formatter.format_json(task, result)
    console.print(json.dumps(summary, indent=2, default=str))


def _output_json_error(task, result):
    """Output JSON error for machine processing"""
    error_summary = {
        "task_id": task.task_id,
        "status": "failed",
        "error": task.error or result.get("error", "Unknown error"),
        "duration_seconds": task.duration_seconds,
        "edits": len(task.edits),
        "logs": [log.get("message", "") for log in task.logs[-5:]]  # Last 5 logs
    }
    console.print(json.dumps(error_summary, indent=2, default=str))


def _output_human_summary(task, result):
    """Output human-readable summary"""
    table = Table(title="Task Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Task ID", task.task_id)
    table.add_row("Status", "✅ Completed")
    table.add_row("Duration", f"{task.duration_seconds:.1f}s")
    table.add_row("Files Changed", str(len(task.edits)))
    table.add_row("Tests Passed", str(len([t for t in task.test_results if t["status"] == "passed"])))
    
    console.print(table)
    
    if task.edits:
        console.print(Panel("[bold]Code Changes[/bold]", expand=False))
        for edit in task.edits:
            console.print(f"  {edit['operation']:8} {edit['file_path']:30} ({edit['lines_changed']:+d} lines)")


def _output_human_error(task, result):
    """Output human-readable error"""
    table = Table(title="Error Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="red")
    
    table.add_row("Task ID", task.task_id)
    table.add_row("Status", "❌ Failed")
    table.add_row("Error", task.error or "Unknown")
    table.add_row("Duration", f"{task.duration_seconds:.1f}s" if task.duration_seconds else "N/A")
    
    console.print(table)
    
    if task.logs:
        console.print(Panel("[bold red]Last 10 Logs[/bold]", expand=False))
        for log in task.logs[-10:]:
            level_color = {"error": "red", "warning": "yellow", "info": "blue", "debug": "dim"}.get(log.get("level"), "white")
            console.print(f"  [{level_color}]{log.get('message', '')}[/]")


# ============================================================================
# Individual stage commands
# ============================================================================

@app.command(help="Generate specifications only")
def spec(
    prompt: str = typer.Argument(..., help="Project description"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r"),
    design: bool = typer.Option(True, "--design/--no-design"),
    tasks: bool = typer.Option(True, "--tasks/--no-tasks"),
    json_output: bool = typer.Option(False, "--json", "-j")
):
    """
    Generate specifications (requirements, design, tasks).
    
    Output is formatted for review and can be piped to other tools.
    """
    try:
        console.print("[bold blue]📋 Generating Specifications...[/bold blue]\n")
        
        task = task_manager.create_task(
            prompt=prompt,
            repo_path=repo or ".",
            tags=["spec-only"]
        )
        
        result = orchestrator.generate_specs_sync(
            task.task_id,
            prompt,
            repo or "."
        )
        
        if json_output:
            console.print(json.dumps(result, indent=2, default=str))
        else:
            console.print(Panel(result.get("requirements", ""), title="[bold]Requirements[/bold]"))
            if design and result.get("design"):
                console.print(Panel(result.get("design"), title="[bold]Design[/bold]"))
            if tasks and result.get("tasks"):
                console.print(Panel("\n".join(result.get("tasks", [])), title="[bold]Tasks[/bold]"))
        
        sys.exit(0)
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@app.command(help="Generate implementation plan")
def plan(
    requirements: str = typer.Option(..., "--requirements", "-r", help="Requirements file or text"),
    design: str = typer.Option(..., "--design", "-d", help="Design file or text"),
    repo: Optional[str] = typer.Option(None, "--repo"),
    json_output: bool = typer.Option(False, "--json", "-j")
):
    """
    Generate an implementation plan from requirements and design.
    
    Can be used to review plan before execution.
    """
    try:
        console.print("[bold blue]📐 Generating Implementation Plan...[/bold blue]\n")
        
        # Load files if paths provided
        req_text = _load_file_or_text(requirements)
        design_text = _load_file_or_text(design)
        
        task = task_manager.create_task(
            prompt=f"Plan: {req_text[:50]}...",
            repo_path=repo or ".",
            tags=["plan-only"]
        )
        
        result = orchestrator.generate_plan_sync(
            task.task_id,
            req_text,
            design_text,
            repo or "."
        )
        
        if json_output:
            console.print(json.dumps(result, indent=2, default=str))
        else:
            _display_plan(result.get("tasks", []), result.get("dependencies", []))
        
        sys.exit(0)
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@app.command(help="Execute implementation from plan")
def implement(
    plan_file: str = typer.Option(..., "--plan", "-p", help="Plan JSON file"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r"),
    auto_approve: bool = typer.Option(False, "--auto-approve", "-a"),
    json_output: bool = typer.Option(False, "--json", "-j")
):
    """
    Execute an implementation plan.
    
    Reads plan from JSON file and generates code.
    """
    try:
        console.print("[bold blue]⚙️  Implementing Plan...[/bold blue]\n")
        
        with open(plan_file) as f:
            plan = json.load(f)
        
        task = task_manager.create_task(
            prompt=str(plan),
            repo_path=repo or ".",
            auto_approve_low_risk=auto_approve,
            tags=["implement-only"]
        )
        
        result = orchestrator.implement_plan_sync(
            task.task_id,
            plan,
            repo or ".",
            task_manager
        )
        
        if json_output:
            console.print(json.dumps(result, indent=2, default=str))
        else:
            console.print(Panel(f"✅ Implementation complete\n\nFiles: {result.get('files_changed', [])}", 
                              title="[bold]Result[/bold]"))
        
        sys.exit(0 if result.get("success") else 1)
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@app.command(help="Run test suite")
def test(
    repo: Optional[str] = typer.Option(None, "--repo", "-r"),
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Test filter pattern"),
    coverage: bool = typer.Option(True, "--coverage/--no-coverage"),
    json_output: bool = typer.Option(False, "--json", "-j")
):
    """
    Run tests on the repository.
    
    Detects test framework automatically (pytest, jest, etc.)
    """
    try:
        console.print("[bold blue]🧪 Running Tests...[/bold blue]\n")
        
        task = task_manager.create_task(
            prompt="Run tests",
            repo_path=repo or ".",
            tags=["test-only"]
        )
        
        result = orchestrator.run_tests_sync(
            task.task_id,
            repo or ".",
            filter,
            coverage,
            task_manager
        )
        
        if json_output:
            console.print(json.dumps(result, indent=2, default=str))
        else:
            _display_test_results(result)
        
        passed = result.get("passed", 0)
        failed = result.get("failed", 0)
        sys.exit(0 if failed == 0 else 1)
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


# ============================================================================
# Utility commands
# ============================================================================

@app.command(help="List all tasks")
def tasks(
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    json_output: bool = typer.Option(False, "--json", "-j"),
    limit: int = typer.Option(10, "--limit", "-l")
):
    """List recent tasks"""
    try:
        status_enum = TaskStatus(status) if status else None
        task_list, total = task_manager.get_tasks(status=status_enum, limit=limit)
        
        if json_output:
            console.print(json.dumps([t.to_dict() for t in task_list], indent=2, default=str))
        else:
            table = Table(title=f"Tasks (showing {len(task_list)}/{total})")
            table.add_column("Task ID", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Progress", style="blue")
            table.add_column("Created", style="dim")
            
            for t in task_list:
                created = t.created_at.strftime("%Y-%m-%d %H:%M:%S")
                table.add_row(t.task_id, t.status.value, f"{t.progress}%", created)
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@app.command(help="Show task details")
def show(
    task_id: str = typer.Argument(..., help="Task ID"),
    json_output: bool = typer.Option(False, "--json", "-j"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow task execution")
):
    """Show detailed task information"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            sys.exit(1)
        
        if json_output:
            console.print(json.dumps(task.to_dict(), indent=2, default=str))
        else:
            _display_task_details(task)
        
        if follow:
            _follow_task(task_id, task_manager)
    
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@app.command(help="View API documentation")
def api(
    start_server: bool = typer.Option(False, "--start", "-s", help="Start API server")
):
    """Access REST API"""
    if start_server:
        from code_alpha.api.server import run_server
        console.print("[bold cyan]Starting API server...[/bold cyan]")
        console.print("📡 API running at http://localhost:8000")
        console.print("📖 Docs available at http://localhost:8000/api/docs")
        run_server()
    else:
        console.print("""
[bold cyan]Code Alpha REST API[/bold cyan]

[bold]Starting the server:[/bold]
  codealpha api --start

[bold]Available endpoints:[/bold]
  
  [cyan]Task Management[/cyan]
  POST   /tasks              - Create new task
  GET    /tasks              - List tasks
  GET    /tasks/{id}         - Get task status
  GET    /tasks/{id}/stream  - Stream task logs (SSE)
  POST   /tasks/{id}/approve - Approve changes
  POST   /tasks/{id}/reject  - Reject changes
  DELETE /tasks/{id}         - Delete task

  [cyan]Pipeline Stages[/cyan]
  POST   /tasks/spec         - Generate specs
  POST   /tasks/plan         - Generate plan
  POST   /tasks/implement    - Execute implementation
  POST   /tasks/test         - Run tests

  [cyan]Control[/cyan]
  POST   /tasks/{id}/pause   - Pause task
  POST   /tasks/{id}/cancel  - Cancel task
  POST   /tasks/{id}/retry   - Retry task

[bold]Documentation:[/bold]
  http://localhost:8000/api/docs  (Interactive Swagger UI)
  http://localhost:8000/api/redoc (ReDoc)
""")


# ============================================================================
# Helper functions
# ============================================================================

def _load_file_or_text(path_or_text: str) -> str:
    """Load from file if path exists, otherwise return text as-is"""
    if os.path.isfile(path_or_text):
        with open(path_or_text) as f:
            return f.read()
    return path_or_text


def _display_plan(tasks: list, dependencies: list):
    """Display implementation plan"""
    if tasks:
        console.print(Panel(f"[bold]Implementation Tasks[/bold]\n\n" + "\n".join(
            f"  • {task.get('name', 'Task')} ({task.get('estimated_hours', 0)}h)"
            for task in tasks
        ), expand=False))


def _display_test_results(result: dict):
    """Display test results"""
    table = Table(title="Test Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Tests", str(result.get("total", 0)))
    table.add_row("Passed", f"[green]{result.get('passed', 0)}[/green]")
    table.add_row("Failed", f"[red]{result.get('failed', 0)}[/red]")
    table.add_row("Duration", f"{result.get('duration', 0):.1f}s")
    
    if result.get("coverage"):
        table.add_row("Coverage", f"{result.get('coverage'):.1f}%")
    
    console.print(table)


def _display_task_details(task):
    """Display task details"""
    console.print(Panel(f"""
[bold]Task: {task.task_id}[/bold]
Status: {task.status.value}
Progress: {task.progress}%
Duration: {task.duration_seconds or 'Running'}s

[bold]Summary:[/bold]
  Files Changed: {len(task.edits)}
  Tests Passed: {len([t for t in task.test_results if t['status'] == 'passed'])}
  Log Entries: {len(task.logs)}
""", expand=False))


def _follow_task(task_id: str, task_manager: TaskManager):
    """Follow task execution in real-time"""
    import time
    console.print("[bold cyan]Following task execution... (Ctrl+C to stop)[/bold cyan]\n")
    
    last_log_count = 0
    try:
        while True:
            task = task_manager.get_task(task_id)
            if not task:
                break
            
            # Print new logs
            if len(task.logs) > last_log_count:
                for log in task.logs[last_log_count:]:
                    level_color = {"error": "red", "warning": "yellow", "info": "blue", "debug": "dim"}.get(log.get("level"), "white")
                    console.print(f"  [{level_color}]{log.get('message', '')}[/]")
                last_log_count = len(task.logs)
            
            # Check if complete
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                console.print(f"\n[bold]{task.status.value.upper()}[/bold]")
                break
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped following[/dim]")


if __name__ == "__main__":
    app()

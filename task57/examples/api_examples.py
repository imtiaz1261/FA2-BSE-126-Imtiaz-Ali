"""
Code Alpha API Examples

Demonstrates programmatic usage of the Code Alpha REST API
for integration with other systems.
"""

import requests
import json
import time
from typing import Dict, Any, Optional
import asyncio


# ==============================================================================
# Basic API Client
# ==============================================================================

class CodeAlphaClient:
    """Simple client for Code Alpha API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def create_task(self, prompt: str, repo_path: str = ".", **kwargs) -> Dict[str, Any]:
        """Create a new task"""
        data = {
            "prompt": prompt,
            "repo_path": repo_path,
            **kwargs
        }
        response = self.session.post(f"{self.base_url}/tasks", json=data)
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        response = self.session.get(f"{self.base_url}/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def list_tasks(self, status: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """List tasks"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        response = self.session.get(f"{self.base_url}/tasks", params=params)
        response.raise_for_status()
        return response.json()
    
    def approve_changes(self, task_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
        """Approve pending changes"""
        data = {"action": "approve"}
        if comment:
            data["comment"] = comment
        response = self.session.post(f"{self.base_url}/tasks/{task_id}/approve", json=data)
        response.raise_for_status()
        return response.json()
    
    def reject_changes(self, task_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Reject pending changes"""
        data = {"action": "reject"}
        if reason:
            data["comment"] = reason
        response = self.session.post(f"{self.base_url}/tasks/{task_id}/reject", json=data)
        response.raise_for_status()
        return response.json()
    
    def stream_logs(self, task_id: str):
        """Stream task logs using Server-Sent Events"""
        response = self.session.get(f"{self.base_url}/tasks/{task_id}/stream", stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                data = line.decode().replace("data: ", "")
                yield json.loads(data)


# ==============================================================================
# Example 1: Basic Usage
# ==============================================================================

def example_basic():
    """Basic task creation and monitoring"""
    print("\n=== Example 1: Basic Usage ===\n")
    
    client = CodeAlphaClient()
    
    # Create task
    task = client.create_task(
        prompt="Add comprehensive test coverage",
        auto_approve_low_risk=True
    )
    
    task_id = task["task_id"]
    print(f"Created task: {task_id}")
    
    # Monitor progress
    while True:
        status = client.get_task_status(task_id)
        print(f"Status: {status['status']} - Progress: {status['progress']}%")
        
        if status['status'] in ['completed', 'failed']:
            break
        
        time.sleep(5)
    
    # Get results
    final_status = client.get_task_status(task_id)
    print(f"\nFinal Status: {final_status['status']}")
    print(f"Files Changed: {len(final_status['edits'])}")
    print(f"Tests Passed: {len([t for t in final_status['test_results'] if t['status'] == 'passed'])}")


# ==============================================================================
# Example 2: Streaming Logs
# ==============================================================================

def example_streaming():
    """Stream task logs in real-time"""
    print("\n=== Example 2: Streaming Logs ===\n")
    
    client = CodeAlphaClient()
    
    # Create task
    task = client.create_task("Improve code quality")
    task_id = task["task_id"]
    
    # Stream logs
    print("Streaming logs...\n")
    for event in client.stream_logs(task_id):
        event_type = event.get("type")
        
        if event_type == "log":
            log = event.get("data", {})
            print(f"[{log.get('level', 'INFO')}] {log.get('message', '')}")
        
        elif event_type == "status":
            print(f"→ {event.get('status')} ({event.get('progress')}%)")
        
        elif event_type == "complete":
            print(f"\n✅ Task complete: {event.get('status')}")
            break


# ==============================================================================
# Example 3: Multi-Stage Pipeline
# ==============================================================================

def example_multi_stage():
    """Execute multi-stage pipeline"""
    print("\n=== Example 3: Multi-Stage Pipeline ===\n")
    
    client = CodeAlphaClient()
    
    # Stage 1: Generate specs
    print("📋 Stage 1: Generating specifications...")
    task1 = client.create_task(
        prompt="Build user authentication system",
        tags=["spec"]
    )
    
    # Wait for completion
    while True:
        status = client.get_task_status(task1["task_id"])
        if status["status"] in ["completed", "failed"]:
            break
        time.sleep(5)
    
    # Stage 2: Generate plan (would use spec output)
    print("📐 Stage 2: Generating plan...")
    task2 = client.create_task(
        prompt="Create implementation plan",
        tags=["plan"]
    )
    
    # Stage 3: Implement
    print("⚙️  Stage 3: Implementing...")
    task3 = client.create_task(
        prompt="Generate code",
        auto_approve_low_risk=True,
        tags=["implement"]
    )
    
    # Stage 4: Test
    print("🧪 Stage 4: Running tests...")
    task4 = client.create_task(
        prompt="Run test suite",
        tags=["test"]
    )
    
    print("\n✅ Pipeline complete!")


# ==============================================================================
# Example 4: Error Handling and Retries
# ==============================================================================

def example_error_handling():
    """Demonstrate error handling"""
    print("\n=== Example 4: Error Handling ===\n")
    
    client = CodeAlphaClient()
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            task = client.create_task("Your task")
            task_id = task["task_id"]
            
            # Monitor with timeout
            start_time = time.time()
            timeout = 60  # seconds
            
            while time.time() - start_time < timeout:
                status = client.get_task_status(task_id)
                
                if status["status"] == "completed":
                    print(f"✅ Task completed: {status['prompt']}")
                    return
                
                elif status["status"] == "failed":
                    error = status.get("error", "Unknown error")
                    print(f"❌ Task failed: {error}")
                    raise Exception(error)
                
                time.sleep(5)
            
            raise TimeoutError("Task execution timeout")
        
        except (requests.RequestException, TimeoutError, Exception) as e:
            retry_count += 1
            print(f"Attempt {retry_count} failed: {e}")
            
            if retry_count < max_retries:
                print(f"Retrying in 10 seconds...")
                time.sleep(10)
            else:
                print("Max retries exceeded")
                raise


# ==============================================================================
# Example 5: Human-in-the-Loop Review
# ==============================================================================

def example_human_review():
    """Demonstrate human review workflow"""
    print("\n=== Example 5: Human-in-the-Loop Review ===\n")
    
    client = CodeAlphaClient()
    
    # Create task (don't auto-approve)
    task = client.create_task(
        prompt="Refactor authentication",
        auto_approve_low_risk=False
    )
    
    task_id = task["task_id"]
    
    # Monitor until approval needed
    while True:
        status = client.get_task_status(task_id)
        
        if status["status"] == "awaiting_approval":
            print("⏸️  Task awaiting approval")
            print(f"Changes:\n{json.dumps(status.get('pending_changes', {}), indent=2)}")
            
            # Simulate human review
            decision = input("\nApprove? (yes/no/request-changes): ").lower()
            
            if decision == "yes":
                client.approve_changes(task_id, "Looks good!")
                print("✅ Changes approved")
            
            elif decision == "no":
                client.reject_changes(task_id, "Needs more work")
                print("❌ Changes rejected")
                break
            
            elif decision == "request-changes":
                comment = input("Feedback: ")
                response = client.session.post(
                    f"{client.base_url}/tasks/{task_id}/request-changes",
                    json={"action": "request_changes", "comment": comment}
                )
                print("💬 Changes requested")
        
        elif status["status"] in ["completed", "failed"]:
            print(f"Task finished: {status['status']}")
            break
        
        time.sleep(5)


# ==============================================================================
# Example 6: Webhook Integration
# ==============================================================================

def example_webhook():
    """Demonstrate webhook notifications"""
    print("\n=== Example 6: Webhook Integration ===\n")
    
    import threading
    
    client = CodeAlphaClient()
    
    # Create task
    task = client.create_task("Your task")
    task_id = task["task_id"]
    
    def monitor_and_notify():
        """Monitor task and send webhook notifications"""
        last_status = None
        
        while True:
            status = client.get_task_status(task_id)
            
            if status["status"] != last_status:
                # Send webhook notification
                notification = {
                    "event": "task_status_changed",
                    "task_id": task_id,
                    "status": status["status"],
                    "progress": status["progress"],
                    "timestamp": time.time()
                }
                
                print(f"🔔 Sending notification: {notification}")
                
                # Would send to webhook endpoint:
                # requests.post("https://hooks.example.com/codealpha", json=notification)
                
                last_status = status["status"]
            
            if status["status"] in ["completed", "failed"]:
                break
            
            time.sleep(5)
    
    # Run in background thread
    monitor_thread = threading.Thread(target=monitor_and_notify, daemon=True)
    monitor_thread.start()
    
    # Keep main thread alive
    monitor_thread.join(timeout=300)


# ==============================================================================
# Example 7: Batch Processing
# ==============================================================================

def example_batch_processing():
    """Process multiple tasks in batch"""
    print("\n=== Example 7: Batch Processing ===\n")
    
    client = CodeAlphaClient()
    
    tasks_to_run = [
        "Add unit tests",
        "Improve error handling",
        "Optimize database queries",
        "Update documentation",
        "Refactor authentication"
    ]
    
    # Create all tasks
    task_ids = []
    for prompt in tasks_to_run:
        task = client.create_task(prompt, auto_approve_low_risk=True)
        task_ids.append(task["task_id"])
        print(f"Created: {prompt} -> {task['task_id']}")
    
    print(f"\nMonitoring {len(task_ids)} tasks...\n")
    
    # Monitor all tasks
    completed = set()
    
    while len(completed) < len(task_ids):
        for task_id in task_ids:
            if task_id in completed:
                continue
            
            status = client.get_task_status(task_id)
            
            if status["status"] in ["completed", "failed"]:
                completed.add(task_id)
                result = "✅" if status["status"] == "completed" else "❌"
                print(f"{result} {task_id}: {status['status']}")
        
        if len(completed) < len(task_ids):
            time.sleep(10)
    
    # Summary
    print("\n📊 Summary:")
    for task_id in task_ids:
        status = client.get_task_status(task_id)
        print(f"  {task_id}: {status['status']}")


# ==============================================================================
# Example 8: Integration with CI/CD
# ==============================================================================

def example_cicd_integration():
    """Demonstrate CI/CD integration"""
    print("\n=== Example 8: CI/CD Integration ===\n")
    
    client = CodeAlphaClient()
    
    # Simulate CI/CD pipeline
    pipeline_config = {
        "on_push": {
            "prompt": "Improve code quality",
            "auto_approve": True
        },
        "on_pr": {
            "prompt": "Add tests for changes",
            "auto_approve": False
        }
    }
    
    # Create task based on trigger
    trigger = "on_push"  # Would come from CI/CD system
    config = pipeline_config[trigger]
    
    print(f"Triggered by: {trigger}")
    
    task = client.create_task(
        prompt=config["prompt"],
        auto_approve_low_risk=config["auto_approve"],
        metadata={
            "ci_system": "github-actions",
            "trigger": trigger,
            "branch": "main"
        }
    )
    
    # Wait for completion
    while True:
        status = client.get_task_status(task["task_id"])
        
        if status["status"] in ["completed", "failed"]:
            # Report to CI/CD
            result = {
                "status": status["status"],
                "files_changed": len(status["edits"]),
                "tests_passed": len([t for t in status["test_results"] if t["status"] == "passed"])
            }
            
            print(f"\nCI/CD Report: {json.dumps(result, indent=2)}")
            
            # Exit with appropriate code
            exit_code = 0 if status["status"] == "completed" else 1
            return exit_code
        
        time.sleep(5)


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    import sys
    
    examples = {
        "1": example_basic,
        "2": example_streaming,
        "3": example_multi_stage,
        "4": example_error_handling,
        "5": example_human_review,
        "6": example_webhook,
        "7": example_batch_processing,
        "8": example_cicd_integration
    }
    
    print("Code Alpha API Examples")
    print("=======================\n")
    
    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("Usage: python api_examples.py [example_number]")
        print("\nAvailable examples:")
        for num, func in examples.items():
            print(f"  {num}: {func.__doc__.strip()}")

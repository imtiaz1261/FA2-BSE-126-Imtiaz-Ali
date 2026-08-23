# Code Alpha CLI & API Documentation

Complete guide for using Code Alpha in CI/CD pipelines, scripts, and automation workflows.

---

## 📋 Table of Contents

1. [Installation](#installation)
2. [CLI Usage](#cli-usage)
3. [API Usage](#api-usage)
4. [CI/CD Integration](#cicd-integration)
5. [Exit Codes](#exit-codes)
6. [Output Formats](#output-formats)
7. [Examples](#examples)

---

## 🔧 Installation

### From Source
```bash
git clone <repo>
cd code_alpha
pip install -e .
pip install -r requirements_cli_api.txt
```

### Via pip (when published)
```bash
pip install codealpha
```

### Docker
```bash
docker build -t codealpha .
docker run -v $(pwd):/workspace codealpha run "your-prompt"
```

---

## 🖥️ CLI Usage

### Main Command: `codealpha run`

Full pipeline execution (spec → plan → implement → test)

```bash
codealpha run "Your task description" [OPTIONS]
```

#### Options

```
--repo PATH                    Path to repository (default: current directory)
-r, --repo PATH               (shorthand)

-a, --auto-approve-low-risk   Automatically approve low-risk changes
                              (useful for CI/CD)

--max-retries NUM             Maximum retry attempts on failure (default: 3)

-t, --timeout SECONDS         Task timeout in seconds (default: 3600)

--on-failure {stop,ask,auto-fix}
                              What to do on test failure (default: ask)

-j, --json                    Output machine-readable JSON
                              (recommended for scripting)

-v, --verbose                 Enable verbose logging

--no-stream                   Don't stream output (useful for CI logs)
```

#### Examples

```bash
# Basic run with defaults
codealpha run "Add comprehensive test coverage"

# Run with auto-approval (for CI)
codealpha run "Refactor code" --auto-approve-low-risk --json

# Run with custom timeout
codealpha run "Complex task" --timeout 7200

# Run on specific repository
codealpha run "Improve code" --repo /path/to/repo

# Run with verbose output
codealpha run "Debug task" --verbose

# Run and capture JSON for processing
codealpha run "Generate API" --json > result.json
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all tests pass, approved) |
| 1 | Failure (test failure, rejected changes, error) |
| 2 | Timeout |
| 3 | Invalid arguments |
| 4 | Configuration error |

---

### Stage Commands

Run individual pipeline stages for advanced control.

#### `codealpha spec`

Generate specifications only.

```bash
codealpha spec "Build authentication system" \
  --repo . \
  --design \
  --tasks \
  --json
```

**Options:**
- `--repo PATH` - Repository path
- `--design/--no-design` - Include design document
- `--tasks/--no-tasks` - Include tasks breakdown
- `-j, --json` - JSON output

#### `codealpha plan`

Generate implementation plan.

```bash
codealpha plan \
  --requirements requirements.md \
  --design design.md \
  --repo . \
  --json
```

**Options:**
- `--requirements TEXT` - Requirements file or text
- `--design TEXT` - Design file or text
- `--repo PATH` - Repository path
- `-j, --json` - JSON output

#### `codealpha implement`

Execute implementation from plan.

```bash
codealpha implement \
  --plan plan.json \
  --repo . \
  --auto-approve \
  --json
```

**Options:**
- `--plan FILE` - Plan JSON file
- `--repo PATH` - Repository path
- `-a, --auto-approve` - Auto-approve changes
- `-j, --json` - JSON output

#### `codealpha test`

Run test suite.

```bash
codealpha test \
  --repo . \
  --filter "test_auth" \
  --coverage \
  --json
```

**Options:**
- `--repo PATH` - Repository path
- `-f, --filter PATTERN` - Test filter pattern
- `--coverage/--no-coverage` - Include coverage
- `-j, --json` - JSON output

---

### Management Commands

#### `codealpha tasks`

List all tasks.

```bash
codealpha tasks --status completed --limit 10 --json
```

**Options:**
- `-s, --status` - Filter by status
- `-l, --limit` - Result limit
- `-j, --json` - JSON output

#### `codealpha show`

Show task details.

```bash
codealpha show task_abc123def456 --json --follow
```

**Options:**
- `-j, --json` - JSON output
- `-f, --follow` - Follow task execution

---

### API Server

#### Start API Server

```bash
codealpha api --start
```

Runs at `http://localhost:8000`

Documentation: `http://localhost:8000/api/docs`

---

## 🔗 API Usage

### Base URL
```
http://localhost:8000
```

### Authentication
Currently unauthenticated. Add JWT in production.

---

### Task Endpoints

#### Create Task

```http
POST /tasks
Content-Type: application/json

{
  "prompt": "Build authentication module",
  "repo_path": "/path/to/repo",
  "auto_approve_low_risk": false,
  "max_retries": 3,
  "timeout_seconds": 3600,
  "on_failure": "ask",
  "tags": ["auth", "security"],
  "metadata": {"priority": "high"}
}
```

**Response:**
```json
{
  "task_id": "task_abc123def456",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00",
  "message": "Task created and queued for execution"
}
```

#### Get Task Status

```http
GET /tasks/{task_id}
```

**Response:**
```json
{
  "task_id": "task_abc123def456",
  "status": "generating",
  "progress": 45,
  "created_at": "2024-01-01T00:00:00",
  "started_at": "2024-01-01T00:00:05",
  "duration_seconds": 25,
  "prompt": "Build authentication module",
  "repo_path": "/path/to/repo",
  "logs": [
    {
      "timestamp": "2024-01-01T00:00:05",
      "level": "info",
      "message": "Starting spec generation..."
    }
  ],
  "edits": [
    {
      "file_path": "auth.py",
      "operation": "create",
      "lines_changed": 150,
      "description": "Created authentication module"
    }
  ],
  "test_results": [
    {
      "test_name": "test_login",
      "status": "passed",
      "duration_seconds": 0.5,
      "output": "PASSED"
    }
  ],
  "current_operation": "Running tests",
  "current_file": null
}
```

#### List Tasks

```http
GET /tasks?status=running&limit=10&offset=0&tags=auth
```

#### Stream Task Logs (SSE)

```http
GET /tasks/{task_id}/stream
```

Real-time Server-Sent Events stream. Useful for web UIs.

```javascript
const eventSource = new EventSource('/tasks/task_abc123/stream');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.data);
};
```

---

### Review & Approval

#### Approve Changes

```http
POST /tasks/{task_id}/approve
Content-Type: application/json

{
  "action": "approve",
  "comment": "Looks good!"
}
```

#### Reject Changes

```http
POST /tasks/{task_id}/reject
Content-Type: application/json

{
  "action": "reject",
  "comment": "Needs more work on error handling"
}
```

#### Request Changes

```http
POST /tasks/{task_id}/request-changes
Content-Type: application/json

{
  "action": "request_changes",
  "comment": "Add docstrings and type hints"
}
```

---

### Pipeline Stages

#### Generate Specs

```http
POST /tasks/spec
Content-Type: application/json

{
  "prompt": "Build authentication system",
  "repo_path": ".",
  "include_design": true,
  "include_tasks": true
}
```

#### Generate Plan

```http
POST /tasks/plan
Content-Type: application/json

{
  "requirements": "User authentication required",
  "design": "OAuth2 with JWT tokens",
  "repo_path": "."
}
```

#### Execute Implementation

```http
POST /tasks/implement
Content-Type: application/json

{
  "plan": { ... },
  "repo_path": ".",
  "auto_test": true,
  "auto_approve": false
}
```

#### Run Tests

```http
POST /tasks/test
Content-Type: application/json

{
  "repo_path": ".",
  "test_filter": "test_auth",
  "coverage": true
}
```

---

### Task Control

#### Pause Task
```http
POST /tasks/{task_id}/pause
```

#### Cancel Task
```http
POST /tasks/{task_id}/cancel
```

#### Retry Failed Task
```http
POST /tasks/{task_id}/retry
```

#### Delete Task
```http
DELETE /tasks/{task_id}
```

---

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
- name: Code Alpha
  run: |
    codealpha run "Your task" \
      --auto-approve-low-risk \
      --json > result.json
```

See `github_actions.yml` for full workflow.

### GitLab CI

```yaml
code-alpha:
  script:
    - codealpha run "Your task" --json > result.json
```

See `gitlab_ci.yml` for full pipeline.

### Jenkins

```groovy
sh '''
  codealpha run "Your task" \
    --auto-approve-low-risk \
    --json > result.json
'''
```

See `Jenkinsfile` for full pipeline.

### Generic CI/CD

Any CI/CD that supports Python and HTTP can integrate:

```bash
#!/bin/bash
# Basic CI/CD integration

# Run Code Alpha
codealpha run "Your task" --json > result.json
EXIT_CODE=$?

# Parse results
PASSED=$(jq '.metrics.passing_tests' result.json)
TOTAL=$(jq '.metrics.total_tests' result.json)

echo "Tests: $PASSED/$TOTAL"

exit $EXIT_CODE  # Exit with Code Alpha status
```

---

## 📊 Output Formats

### JSON Output

```bash
codealpha run "task" --json
```

```json
{
  "task_id": "task_...",
  "status": "completed",
  "success": true,
  "duration_seconds": 45.5,
  "execution": {
    "specs_generated": true,
    "plan_created": true,
    "code_generated": true,
    "tests_passed": true,
    "all_approved": true
  },
  "metrics": {
    "total_edits": 5,
    "total_lines_changed": 234,
    "total_tests": 15,
    "passing_tests": 15,
    "failing_tests": 0
  },
  "changes": {
    "files_created": 2,
    "files_modified": 3,
    "files_deleted": 0
  },
  "artifacts": {
    "spec_path": ".codealpha/specs/requirements.md",
    "plan_path": ".codealpha/tasks/plan.json",
    "log_path": ".codealpha/logs/task.log",
    "pr_created": true,
    "pr_url": "https://github.com/..."
  }
}
```

### Human-Readable Output

```
✅ Task completed successfully!

Task Summary
┌─────────────┬───────────────────────┐
│ Metric      │ Value                 │
├─────────────┼───────────────────────┤
│ Task ID     │ task_abc123def456     │
│ Status      │ ✅ Completed          │
│ Duration    │ 45.5s                 │
│ Files       │ 5                     │
│ Tests       │ 15/15 passed          │
└─────────────┴───────────────────────┘

Code Changes
  create   src/auth.py                     (+150 lines)
  modify   src/api.py                      (+45 lines)
  modify   tests/test_auth.py              (+89 lines)
  create   src/models.py                   (+56 lines)
  modify   requirements.txt                (+2 lines)
```

### JUnit XML (for CI integration)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="15" failures="0" passed="15">
  <testsuite name="CodeAlpha" tests="15" failures="0">
    <testcase name="test_login" classname="auth"/>
    <testcase name="test_register" classname="auth"/>
    ...
  </testsuite>
</testsuites>
```

### Slack Notification

```json
{
  "attachments": [
    {
      "color": "good",
      "title": "✅ Code Alpha Task Success",
      "fields": [
        {"title": "Status", "value": "COMPLETED", "short": true},
        {"title": "Duration", "value": "45.5s", "short": true},
        {"title": "Files Changed", "value": "5", "short": true},
        {"title": "Tests Passed", "value": "15/15", "short": true}
      ]
    }
  ]
}
```

---

## 📝 Examples

### Example 1: Generate and Auto-Approve

```bash
#!/bin/bash

# Generate code with auto-approval
codealpha run "Add user authentication" \
  --auto-approve-low-risk \
  --repo . \
  --json > result.json

# Parse and check results
if jq -e '.success' result.json > /dev/null; then
  echo "✅ Code generation successful"
  FILES=$(jq '.metrics.total_edits' result.json)
  echo "📝 Files modified: $FILES"
  exit 0
else
  echo "❌ Code generation failed"
  jq '.error' result.json
  exit 1
fi
```

### Example 2: API-Driven Workflow

```python
import requests
import json
import time

# Create task
response = requests.post('http://localhost:8000/tasks', json={
    'prompt': 'Add email validation',
    'auto_approve_low_risk': True
})
task = response.json()
task_id = task['task_id']

print(f"Created task: {task_id}")

# Monitor progress
while True:
    response = requests.get(f'http://localhost:8000/tasks/{task_id}')
    task = response.json()
    
    print(f"Progress: {task['progress']}% - {task['status']}")
    
    if task['status'] in ['completed', 'failed']:
        break
    
    time.sleep(5)

# Get final results
print(json.dumps(task, indent=2))
```

### Example 3: Multi-Stage Pipeline

```bash
#!/bin/bash

PROMPT="Build user management system"
REPO="."

# Stage 1: Generate specs
echo "📋 Generating specifications..."
codealpha spec "$PROMPT" --repo $REPO > spec.json

# Stage 2: Generate plan
REQ=$(jq -r '.requirements' spec.json)
DESIGN=$(jq -r '.design' spec.json)

echo "📐 Generating plan..."
codealpha plan --requirements "$REQ" --design "$DESIGN" > plan.json

# Stage 3: Implement
echo "⚙️  Implementing..."
codealpha implement --plan plan.json --auto-approve

# Stage 4: Test
echo "🧪 Running tests..."
codealpha test --repo $REPO --coverage

echo "✅ Pipeline complete!"
```

### Example 4: GitHub Actions Integration

```yaml
name: Code Generation CI

on: [push, pull_request]

jobs:
  codealpha:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - run: pip install codealpha
      
      - name: Generate Code
        run: |
          codealpha run "Implement new features" \
            --auto-approve-low-risk \
            --json > result.json
      
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: code-alpha-results
          path: result.json
```

---

## 🔐 Security Considerations

1. **API Authentication**: Add JWT or OAuth2 in production
2. **Repository Access**: Use SSH keys or secure credentials
3. **Secrets Management**: Use environment variables or secret vaults
4. **Rate Limiting**: Implement on API endpoints
5. **Audit Logging**: Log all task executions
6. **Code Review**: Always review generated code before merging

---

## 🐛 Troubleshooting

### Task Times Out

Increase timeout:
```bash
codealpha run "task" --timeout 7200
```

### Tests Fail

Check auto-fix mode:
```bash
codealpha run "task" --on-failure auto-fix
```

### API Not Responding

Ensure server is running:
```bash
codealpha api --start
```

### JSON Parsing Issues

Use `jq` for validation:
```bash
codealpha run "task" --json | jq .
```

---

## 📚 API Reference

Full API documentation available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

---

## 📞 Support

- GitHub Issues: Submit bug reports
- Documentation: See `CLI_API_README.md`
- Examples: Check `ci_examples/` directory

---

**Status**: ✅ Production Ready

**Version**: 0.1.0

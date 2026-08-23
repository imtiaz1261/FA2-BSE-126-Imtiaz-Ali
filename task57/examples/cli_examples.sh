#!/bin/bash
# Code Alpha CLI Examples

# ==============================================================================
# Example 1: Basic Run with Auto-Approval
# ==============================================================================

echo "Example 1: Basic Run"
codealpha run "Add comprehensive test coverage" \
  --auto-approve-low-risk \
  --repo . \
  --json > result.json

# Check success
if jq -e '.success' result.json > /dev/null; then
  echo "✅ Success!"
  jq '.metrics' result.json
else
  echo "❌ Failed"
  jq '.error' result.json
fi


# ==============================================================================
# Example 2: Multi-Stage Pipeline
# ==============================================================================

echo "Example 2: Multi-Stage Pipeline"

PROMPT="Build user authentication system"
REPO="."

# Stage 1: Generate specs
echo "📋 Generating specifications..."
codealpha spec "$PROMPT" --repo $REPO --json > spec.json

# Extract specs
REQ=$(jq -r '.requirements' spec.json)
DESIGN=$(jq -r '.design' spec.json)

# Stage 2: Generate plan
echo "📐 Generating plan..."
codealpha plan \
  --requirements "$REQ" \
  --design "$DESIGN" \
  --repo $REPO \
  --json > plan.json

# Stage 3: Implement
echo "⚙️  Implementing..."
PLAN=$(cat plan.json)
codealpha implement \
  --plan plan.json \
  --repo $REPO \
  --auto-approve \
  --json > implementation.json

# Stage 4: Test
echo "🧪 Running tests..."
codealpha test \
  --repo $REPO \
  --coverage \
  --json > tests.json

# Summary
echo "✅ Pipeline complete!"
echo "Results: spec.json, plan.json, implementation.json, tests.json"


# ==============================================================================
# Example 3: Filtering and Monitoring
# ==============================================================================

echo "Example 3: Task Monitoring"

# List running tasks
codealpha tasks --status running --limit 5 --json | jq '.tasks[] | {id: .task_id, status: .status, progress: .progress}'

# Show specific task
TASK_ID="task_abc123"
codealpha show $TASK_ID --follow


# ==============================================================================
# Example 4: CI/CD Integration (GitHub Actions style)
# ==============================================================================

echo "Example 4: CI/CD Integration"

#!/bin/bash
set -e  # Exit on error

PROMPT="${1:-Improve code quality}"
REPO="${2:-.}"

# Run Code Alpha
echo "🚀 Running Code Alpha..."
codealpha run "$PROMPT" \
  --repo "$REPO" \
  --auto-approve-low-risk \
  --max-retries 3 \
  --timeout 3600 \
  --json > result.json

EXIT_CODE=$?

# Parse results
if [ $EXIT_CODE -eq 0 ]; then
  PASSED=$(jq '.metrics.passing_tests' result.json)
  TOTAL=$(jq '.metrics.total_tests' result.json)
  FILES=$(jq '.metrics.total_edits' result.json)
  
  echo "✅ Code Alpha completed successfully"
  echo "📊 Tests: $PASSED/$TOTAL"
  echo "📝 Files: $FILES"
  
  # Upload results (example: to S3)
  # aws s3 cp result.json s3://my-bucket/codealpha-results/
  
  exit 0
else
  echo "❌ Code Alpha failed"
  jq '.error' result.json
  exit 1
fi


# ==============================================================================
# Example 5: Error Handling and Retries
# ==============================================================================

echo "Example 5: Error Handling"

MAX_ATTEMPTS=3
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  echo "Attempt $ATTEMPT/$MAX_ATTEMPTS..."
  
  if codealpha run "Your task" --json > result.json; then
    if jq -e '.success' result.json > /dev/null; then
      echo "✅ Success!"
      exit 0
    fi
  fi
  
  ATTEMPT=$((ATTEMPT + 1))
  
  if [ $ATTEMPT -le $MAX_ATTEMPTS ]; then
    echo "⏳ Retrying in 10 seconds..."
    sleep 10
  fi
done

echo "❌ Failed after $MAX_ATTEMPTS attempts"
exit 1


# ==============================================================================
# Example 6: Output Formatting for Different Destinations
# ==============================================================================

echo "Example 6: Output Formatting"

# Run once
codealpha run "task" --json > result.json

# Format for different systems
echo "GitHub Actions format:"
jq '.metrics | to_entries[] | "::set-output name=\(.key)::\(.value)"' result.json

echo "GitLab CI format:"
jq '{passed: .metrics.passing_tests, failed: .metrics.failing_tests}' result.json

echo "Slack notification:"
jq '{text: "Code Alpha: \(.status)", attachments: [{color: (if .success then "good" else "danger" end), fields: [{title: "Tests", value: "\(.metrics.passing_tests)/\(.metrics.total_tests)"}]}]}' result.json

echo "Jenkins XML:"
jq -r '.test_results | "<?xml version=\"1.0\"?><testsuites>" + (
  map("<testsuite><testcase name=\"\(.test_name)\" " + (if .status == "passed" then "/>" else "><failure/></testcase>" end))
  | join("")
) + "</testsuites>"' result.json


# ==============================================================================
# Example 7: Parallel Execution
# ==============================================================================

echo "Example 7: Parallel Tasks"

# Run multiple tasks in parallel
for task in "Add tests" "Fix linting" "Update docs"; do
  echo "Starting: $task"
  (codealpha run "$task" --json > "result_$(date +%s).json") &
done

# Wait for all background jobs
wait
echo "✅ All tasks completed"


# ==============================================================================
# Example 8: Custom Configuration
# ==============================================================================

echo "Example 8: Custom Configuration"

# Create config file
cat > codealpha.config.json << 'EOF'
{
  "repo_path": ".",
  "auto_approve_low_risk": true,
  "max_retries": 5,
  "timeout_seconds": 7200,
  "on_failure": "auto-fix",
  "tags": ["ci", "automated"],
  "metadata": {
    "pipeline": "github-actions",
    "triggered_by": "push",
    "branch": "main"
  }
}
EOF

# Use config
CONFIG=$(cat codealpha.config.json)
PROMPT=$(echo $CONFIG | jq -r '.repo_path')

codealpha run "Your task" \
  --repo $(echo $CONFIG | jq -r '.repo_path') \
  --auto-approve-low-risk=$(echo $CONFIG | jq -r '.auto_approve_low_risk') \
  --max-retries $(echo $CONFIG | jq -r '.max_retries') \
  --timeout $(echo $CONFIG | jq -r '.timeout_seconds')


# ==============================================================================
# Example 9: Logging and Debugging
# ==============================================================================

echo "Example 9: Debugging"

# Run with verbose output
codealpha run "debug task" --verbose --json > result.json

# Extract logs
jq '.logs[]' result.json | while read -r line; do
  LEVEL=$(echo $line | jq -r '.level')
  MSG=$(echo $line | jq -r '.message')
  echo "[$LEVEL] $MSG"
done


# ==============================================================================
# Example 10: Integration with External Tools
# ==============================================================================

echo "Example 10: External Tools Integration"

# Run and notify via webhook
codealpha run "task" --json > result.json

# Send to external service
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK \
  -H 'Content-Type: application/json' \
  -d @<(jq '{
    text: "Code Alpha Task Complete",
    attachments: [{
      color: (if .success then "good" else "danger" end),
      fields: [
        {title: "Status", value: .status, short: true},
        {title: "Files", value: .metrics.total_edits, short: true}
      ]
    }]
  }' result.json)

# Send to monitoring system
METRICS=$(jq '{
  success: .success,
  duration_seconds: .duration_seconds,
  files_changed: .metrics.total_edits,
  tests_passed: .metrics.passing_tests
}' result.json)

curl -X POST http://monitoring.local/metrics \
  -H 'Content-Type: application/json' \
  -d "$METRICS"

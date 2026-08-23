"""
Output formatting for CLI and API responses.

Provides human-readable and machine-readable formats for task results.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from code_alpha.api.task_manager import Task


class OutputFormatter:
    """Formats task output for various destinations"""
    
    def format_json(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format as machine-readable JSON"""
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "success": result.get("success", False),
            "duration_seconds": task.duration_seconds,
            "timestamp": datetime.utcnow().isoformat(),
            
            # Execution summary
            "execution": {
                "specs_generated": result.get("specs_generated", False),
                "plan_created": result.get("plan_created", False),
                "code_generated": result.get("code_generated", False),
                "tests_passed": result.get("tests_passed", False),
                "all_approved": result.get("all_approved", True)
            },
            
            # Metrics
            "metrics": {
                "total_edits": len(task.edits),
                "total_lines_changed": sum(e.get("lines_changed", 0) for e in task.edits),
                "total_tests": len(task.test_results),
                "passing_tests": len([t for t in task.test_results if t.get("status") == "passed"]),
                "failing_tests": len([t for t in task.test_results if t.get("status") == "failed"]),
                "coverage_delta": result.get("coverage_delta")
            },
            
            # Changes
            "changes": {
                "files_created": len([e for e in task.edits if e.get("operation") == "create"]),
                "files_modified": len([e for e in task.edits if e.get("operation") == "modify"]),
                "files_deleted": len([e for e in task.edits if e.get("operation") == "delete"])
            },
            
            # Artifacts
            "artifacts": {
                "spec_path": result.get("spec_path"),
                "plan_path": result.get("plan_path"),
                "log_path": result.get("log_path"),
                "pr_created": result.get("pr_created", False),
                "pr_url": result.get("pr_url")
            },
            
            # Errors
            "error": task.error or result.get("error"),
            "recommendations": result.get("recommendations", []),
            
            # Details
            "edits": [
                {
                    "file": e.get("file_path"),
                    "operation": e.get("operation"),
                    "lines": e.get("lines_changed"),
                    "description": e.get("description")
                }
                for e in task.edits
            ],
            
            "tests": [
                {
                    "name": t.get("test_name"),
                    "status": t.get("status"),
                    "duration_seconds": t.get("duration_seconds"),
                    "error": t.get("error_message")
                }
                for t in task.test_results
            ],
            
            "logs": [
                {
                    "timestamp": log.get("timestamp"),
                    "level": log.get("level"),
                    "message": log.get("message")
                }
                for log in task.logs
            ]
        }
    
    def format_github_ci(self, task: Task, result: Dict[str, Any]) -> str:
        """Format for GitHub Actions CI output"""
        lines = [
            "## 🤖 Code Alpha Task Report",
            "",
            f"**Task ID:** {task.task_id}",
            f"**Status:** {task.status.value}",
            f"**Duration:** {task.duration_seconds:.1f}s" if task.duration_seconds else "**Duration:** Running",
            "",
            "### Summary",
            f"- ✅ Files Modified: {len([e for e in task.edits if e.get('operation') == 'modify'])}",
            f"- ✨ Files Created: {len([e for e in task.edits if e.get('operation') == 'create'])}",
            f"- 📋 Tests Passed: {len([t for t in task.test_results if t.get('status') == 'passed'])}/{len(task.test_results)}",
            "",
        ]
        
        if task.edits:
            lines.extend([
                "### Changes",
                ""
            ])
            for edit in task.edits[:10]:  # Show first 10
                lines.append(f"- `{edit.get('operation')}` {edit.get('file_path')} ({edit.get('lines_changed'):+d} lines)")
        
        if task.error:
            lines.extend([
                "",
                "### ❌ Error",
                f"```\n{task.error}\n```"
            ])
        
        return "\n".join(lines)
    
    def format_gitlab_ci(self, task: Task, result: Dict[str, Any]) -> str:
        """Format for GitLab CI output"""
        report = {
            "summary": {
                "task_id": task.task_id,
                "status": task.status.value,
                "duration_seconds": task.duration_seconds or 0,
                "files_changed": len(task.edits),
                "tests_passed": len([t for t in task.test_results if t.get("status") == "passed"]),
                "tests_failed": len([t for t in task.test_results if t.get("status") == "failed"])
            },
            "changes": [
                {
                    "path": e.get("file_path"),
                    "new_line": e.get("lines_changed", 0) if e.get("operation") in ["create", "modify"] else 0,
                    "old_line": 0 if e.get("operation") == "create" else e.get("lines_changed", 0)
                }
                for e in task.edits
            ]
        }
        return json.dumps(report, indent=2)
    
    def format_jenkins(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format for Jenkins"""
        return {
            "build_name": f"Code Alpha - {task.task_id}",
            "status": "SUCCESS" if result.get("success") else "FAILURE",
            "result": {
                "duration_seconds": task.duration_seconds or 0,
                "artifacts": {
                    "files_changed": len(task.edits),
                    "test_results": len(task.test_results)
                },
                "error_details": task.error or None
            }
        }
    
    def format_slack_message(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format for Slack notifications"""
        status_icon = "✅" if result.get("success") else "❌"
        status_color = "good" if result.get("success") else "danger"
        
        return {
            "attachments": [
                {
                    "color": status_color,
                    "title": f"{status_icon} Code Alpha Task {task.task_id}",
                    "fields": [
                        {
                            "title": "Status",
                            "value": task.status.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Duration",
                            "value": f"{task.duration_seconds:.1f}s" if task.duration_seconds else "N/A",
                            "short": True
                        },
                        {
                            "title": "Files Changed",
                            "value": str(len(task.edits)),
                            "short": True
                        },
                        {
                            "title": "Tests Passed",
                            "value": f"{len([t for t in task.test_results if t.get('status') == 'passed'])}/{len(task.test_results)}",
                            "short": True
                        }
                    ],
                    "footer": "Code Alpha",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
    
    def format_junit_xml(self, task: Task) -> str:
        """Format test results as JUnit XML (for CI tools)"""
        failed_count = len([t for t in task.test_results if t.get("status") == "failed"])
        passed_count = len([t for t in task.test_results if t.get("status") == "passed"])
        total = len(task.test_results)
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<testsuites tests="{total}" failures="{failed_count}" passed="{passed_count}">',
            f'  <testsuite name="CodeAlpha" tests="{total}" failures="{failed_count}">',
        ]
        
        for test in task.test_results:
            test_name = test.get("test_name", "Unknown")
            status = test.get("status", "skipped")
            
            if status == "failed":
                xml_lines.append(f'    <testcase name="{test_name}" classname="code_alpha">')
                xml_lines.append(f'      <failure>{test.get("error_message", "Test failed")}</failure>')
                xml_lines.append('    </testcase>')
            else:
                xml_lines.append(f'    <testcase name="{test_name}" classname="code_alpha"/>')
        
        xml_lines.extend([
            '  </testsuite>',
            '</testsuites>'
        ])
        
        return "\n".join(xml_lines)
    
    def format_cobertura_xml(self, task: Task, coverage_data: Optional[Dict[str, Any]] = None) -> str:
        """Format coverage data as Cobertura XML"""
        coverage_percent = coverage_data.get("total", 0) if coverage_data else 0
        
        xml_lines = [
            '<?xml version="1.0"?>',
            f'<coverage version="1.0" line-rate="{coverage_percent/100:.2f}" branch-rate="0" lines-valid="{coverage_data.get("lines_valid", 0) if coverage_data else 0}" lines-covered="{coverage_data.get("lines_covered", 0) if coverage_data else 0}" branches-covered="0" branches-valid="0" complexity="0" timestamp="{int(datetime.utcnow().timestamp())*1000}">',
            '  <packages/>',
            '</coverage>'
        ]
        
        return "\n".join(xml_lines)
    
    def format_trx(self, task: Task) -> str:
        """Format test results as TRX (Visual Studio Test Results)"""
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<TestRun id="CodeAlpha-{task.task_id}" xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">',
            '  <ResultSummary outcome="Passed">',
            '  </ResultSummary>',
            '  <Results>',
        ]
        
        for test in task.test_results:
            test_id = hash(test.get("test_name", "")) % 10000
            outcome = "Passed" if test.get("status") == "passed" else "Failed"
            xml_lines.append(f'    <UnitTestResult testName="{test.get("test_name")}" outcome="{outcome}" testId="{test_id}"/>')
        
        xml_lines.extend([
            '  </Results>',
            '</TestRun>'
        ])
        
        return "\n".join(xml_lines)
    
    def generate_report(self, task: Task, result: Dict[str, Any], format: str = "json") -> str:
        """Generate report in specified format"""
        formatters = {
            "json": lambda: json.dumps(self.format_json(task, result), indent=2, default=str),
            "github": lambda: self.format_github_ci(task, result),
            "gitlab": lambda: self.format_gitlab_ci(task, result),
            "jenkins": lambda: json.dumps(self.format_jenkins(task, result), indent=2),
            "slack": lambda: json.dumps(self.format_slack_message(task, result), indent=2),
            "junit": lambda: self.format_junit_xml(task),
            "cobertura": lambda: self.format_cobertura_xml(task),
            "trx": lambda: self.format_trx(task)
        }
        
        if format not in formatters:
            raise ValueError(f"Unknown format: {format}")
        
        return formatters[format]()

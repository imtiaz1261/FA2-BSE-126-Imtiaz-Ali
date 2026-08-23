"""
ReAct (Reasoning + Acting) agent orchestration for code tasks.

Implements the ReAct loop: Thought → Action → Observation → Reflection
With self-correction on test failures.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models_agent import AgentPhase, AgentReasoningStep, ProposedCodeChange, AgentSession
from app.services.agent_tools import AgentTools, ToolResult
from app.services.docker_sandbox import SandboxContainer, SandboxConfig

logger = logging.getLogger(__name__)


# ============================================================================
# ReAct Agent
# ============================================================================


class ReactAgent:
    """ReAct-style coding agent with self-correction."""

    def __init__(
        self,
        session: AgentSession,
        tools: AgentTools,
        sandbox: SandboxContainer,
        llm_provider,  # Vision LLM or API client
    ):
        """
        Initialize ReAct agent.

        Args:
            session: Agent session record
            tools: Agent tools instance
            sandbox: Sandbox container
            llm_provider: LLM API client
        """
        self.session = session
        self.tools = tools
        self.sandbox = sandbox
        self.llm = llm_provider
        self.iteration = 0
        self.reasoning_steps = []

    async def run(
        self,
        task: str,
        db: AsyncSession,
    ) -> AsyncGenerator[dict, None]:
        """
        Run the ReAct loop.

        Args:
            task: Natural language coding task
            db: Database session

        Yields:
            Reasoning steps and updates as they occur
        """
        try:
            # Phase 1: Planning
            await self._update_phase(db, AgentPhase.planning)
            yield {"type": "phase", "phase": "planning"}

            # Get initial plan from LLM
            plan = await self._get_plan(task)
            yield {
                "type": "reasoning",
                "step": "thought",
                "content": plan,
            }

            # Phase 2: Main loop
            while self.iteration < self.session.max_self_corrections + 1:
                self.iteration += 1
                yield {"type": "iteration", "iteration": self.iteration}

                # Read files
                await self._update_phase(db, AgentPhase.reading_files)
                files_summary = await self._read_relevant_files(task)
                yield {
                    "type": "reasoning",
                    "step": "observation",
                    "content": f"Read files:\n{files_summary}",
                }

                # Propose changes
                await self._update_phase(db, AgentPhase.proposing_changes)
                changes = await self._propose_changes(task, plan)

                for change_proposal in changes:
                    yield {
                        "type": "change_proposed",
                        "file": change_proposal["file"],
                        "operation": change_proposal["operation"],
                        "diff": change_proposal["diff"],
                    }

                    # Store in database
                    proposed_change = ProposedCodeChange(
                        session_id=self.session.id,
                        file_path=change_proposal["file"],
                        operation=change_proposal["operation"],
                        original_content=change_proposal.get("original"),
                        proposed_content=change_proposal.get("proposed"),
                        diff=change_proposal["diff"],
                    )
                    db.add(proposed_change)

                await db.commit()

                # Phase 3: Await approval
                await self._update_phase(db, AgentPhase.awaiting_approval)
                yield {"type": "awaiting_approval", "changes_count": len(changes)}

                # Wait for approval (this would be handled by frontend)
                # For now, assume automatic approval for testing
                # In production, this would wait for user input
                approved = True  # TODO: Wait for approval from frontend

                if not approved:
                    yield {
                        "type": "change_rejected",
                        "message": "User rejected changes",
                    }
                    continue

                # Apply changes
                await self.tools.apply_staged_changes()
                yield {"type": "changes_applied"}

                # Phase 4: Run tests
                await self._update_phase(db, AgentPhase.testing)
                test_result = await self._run_tests()

                yield {
                    "type": "test_result",
                    "passed": test_result["passed"],
                    "output": test_result["output"],
                }

                # Check if tests passed
                if test_result["passed"]:
                    await self._update_phase(db, AgentPhase.complete)
                    yield {
                        "type": "complete",
                        "summary": "Task completed successfully",
                    }
                    break

                # Self-correction
                if self.iteration < self.session.max_self_corrections:
                    self.session.self_corrections += 1
                    await self._update_phase(db, AgentPhase.self_correcting)

                    correction = await self._analyze_failure(
                        test_result["output"],
                        task,
                    )

                    yield {
                        "type": "reasoning",
                        "step": "thought",
                        "content": f"Self-correction: {correction}",
                    }

                    plan = correction  # Update plan for next iteration
                else:
                    raise Exception("Max self-corrections reached")

        except Exception as e:
            logger.error(f"Agent error: {e}")
            await self._update_phase(db, AgentPhase.failed)
            self.session.error_message = str(e)
            await db.commit()

            yield {
                "type": "error",
                "message": str(e),
                "iterations": self.iteration,
            }

    # ========================================================================
    # LLM Interactions
    # ========================================================================

    async def _get_plan(self, task: str) -> str:
        """Get initial plan from LLM."""
        prompt = f"""You are a skilled coding assistant. Analyze this task and create a detailed plan:

Task: {task}

Provide a step-by-step plan of what you'll do. Be specific about which files you'll read and modify."""

        # This would call the actual LLM
        # For now, return a template
        return (
            "1. Analyze the task requirements\n"
            "2. Read relevant source files\n"
            "3. Identify files to modify\n"
            "4. Propose changes\n"
            "5. Run tests\n"
            "6. Iterate if needed"
        )

    async def _read_relevant_files(self, task: str) -> str:
        """Read relevant files based on task."""
        # This would use LLM to determine which files are relevant
        # For now, just list the repo structure
        result = self.tools.list_files()
        return result.output if result.success else "Could not read files"

    async def _propose_changes(self, task: str, plan: str) -> list[dict]:
        """Propose code changes."""
        # This would call LLM to generate specific changes
        # For now, return empty list
        return []

    async def _analyze_failure(self, test_output: str, task: str) -> str:
        """Analyze test failure and propose correction."""
        prompt = f"""The task failed with this test output:

{test_output}

Original task: {task}

What should be done to fix this? Be specific about file changes."""

        # This would call LLM
        return "Analysis of failure and proposed fixes"

    # ========================================================================
    # Tool Execution
    # ========================================================================

    async def _run_tests(self) -> dict:
        """Run tests and return results."""
        result = await self.tools.run_tests()

        return {
            "passed": result.success,
            "output": result.output or result.error or "Unknown error",
        }

    # ========================================================================
    # Database Updates
    # ========================================================================

    async def _update_phase(
        self,
        db: AsyncSession,
        phase: AgentPhase,
    ) -> None:
        """Update session phase."""
        self.session.phase = phase
        self.session.total_iterations = self.iteration
        await db.commit()

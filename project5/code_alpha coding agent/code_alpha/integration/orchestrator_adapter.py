"""
Adapter for integrating ContextManager into Orchestrator.

Provides drop-in integration without modifying existing orchestrator code.
"""

import logging
from typing import Optional, Callable, Any, Dict
import functools

from .context_manager import ContextManager, TaskContext

logger = logging.getLogger(__name__)


class OrchestratorAdapter:
    """
    Adapter wrapping orchestrator with integrated context management.
    
    Intercepts orchestrator methods to:
    - Inject memory context into prompts
    - Track task progress in real-time
    - Extract conventions after completion
    - Send status updates to extension/dashboard
    """
    
    def __init__(
        self,
        orchestrator: Any,
        context_manager: ContextManager,
    ):
        self.orchestrator = orchestrator
        self.context_manager = context_manager
        self.current_task_id: Optional[str] = None
    
    async def run_with_context(
        self,
        task_id: str,
        task_description: str,
        repo_root: str,
        run_fn: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run task with integrated context management.
        
        Args:
            task_id: Task identifier
            task_description: Task description
            repo_root: Repository root
            run_fn: Orchestrator method to run
            **kwargs: Arguments to pass to run_fn
        
        Returns:
            Result from orchestrator with metrics
        """
        # Create task context
        context = self.context_manager.create_task_context(
            task_id=task_id,
            task_description=task_description,
        )
        
        self.current_task_id = task_id
        
        try:
            # Inject memory context into kwargs if prompt-based
            if 'prompt' in kwargs:
                memory_context = context.memory_conventions
                if memory_context:
                    kwargs['prompt'] = (
                        f"{kwargs['prompt']}\n\n"
                        f"## Project Conventions\n{memory_context}"
                    )
            
            # Execute orchestrator function
            result = await run_fn(**kwargs)
            
            # Update progress
            await self.context_manager.update_task_status(
                task_id=task_id,
                phase="completed",
                progress=100,
            )
            
            # Extract metrics and complete task
            metrics = await self.context_manager.complete_task(task_id)
            
            # Attach metrics to result
            result['_metrics'] = metrics.to_dict()
            
            return result
        
        except Exception as e:
            logger.error(f"Error in task {task_id}: {e}")
            await self.context_manager.record_error(task_id, str(e))
            raise
        
        finally:
            self.current_task_id = None
    
    def wrap_stage(self, stage_name: str):
        """
        Decorator to wrap orchestrator stage methods.
        
        Usage:
            @adapter.wrap_stage("planning")
            async def my_planning_stage(...):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if self.current_task_id:
                    # Update status to this stage
                    await self.context_manager.update_task_status(
                        task_id=self.current_task_id,
                        phase=stage_name,
                        progress=kwargs.get('progress', 0),
                    )
                
                # Call original function
                result = await func(*args, **kwargs)
                
                return result
            
            return wrapper
        
        return decorator
    
    def get_injected_prompt(self, base_prompt: str) -> str:
        """
        Get prompt with injected memory context.
        
        Args:
            base_prompt: Original prompt
        
        Returns:
            Prompt with memory context injected
        """
        if not self.current_task_id:
            return base_prompt
        
        memory_context = self.context_manager.get_memory_context(self.current_task_id)
        
        if memory_context:
            return f"{base_prompt}\n\n## Project Conventions\n{memory_context}"
        
        return base_prompt


def create_integrated_orchestrator(
    orchestrator: Any,
    context_manager: ContextManager,
) -> OrchestratorAdapter:
    """
    Factory function to create integrated orchestrator.
    
    Args:
        orchestrator: Original orchestrator instance
        context_manager: ContextManager for integration
    
    Returns:
        OrchestratorAdapter wrapping orchestrator
    """
    return OrchestratorAdapter(orchestrator, context_manager)


async def run_integrated_task(
    context_manager: ContextManager,
    task_id: str,
    task_description: str,
    repo_root: str,
    orchestrator_fn: Callable,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to run task with full integration.
    
    Args:
        context_manager: ContextManager instance
        task_id: Task identifier
        task_description: Task description
        repo_root: Repository root
        orchestrator_fn: Orchestrator method to run
        **kwargs: Arguments for orchestrator
    
    Returns:
        Orchestrator result with metrics attached
    """
    adapter = OrchestratorAdapter(None, context_manager)
    
    return await adapter.run_with_context(
        task_id=task_id,
        task_description=task_description,
        repo_root=repo_root,
        run_fn=orchestrator_fn,
        **kwargs
    )

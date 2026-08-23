"""
RAG/Agent Worker Process

Handles:
- Document ingestion and processing
- Embedding generation
- Vector indexing
- Long-running AI tasks
- Agent sandbox jobs

Run with: python -m app.worker.main
"""

import asyncio
import logging
import signal
from typing import Optional

from app.config import settings
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


class WorkerProcess:
    """Main worker process manager."""

    def __init__(self):
        self.running = True
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the worker process."""
        self.logger.info(
            f"Starting worker process ({settings.app_name})",
            extra={
                "environment": settings.environment,
                "log_level": settings.log_level,
            },
        )

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, self._handle_shutdown)
        loop.add_signal_handler(signal.SIGINT, self._handle_shutdown)

        try:
            # Import worker tasks
            from app.worker import tasks

            # Start worker task processors
            await asyncio.gather(
                tasks.process_document_ingestion_queue(),
                tasks.process_embedding_queue(),
                tasks.process_agent_jobs_queue(),
                # Add more workers as needed
                return_exceptions=True,
            )
        except Exception as e:
            self.logger.error(f"Worker error: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()

    def _handle_shutdown(self):
        """Handle shutdown signal."""
        self.logger.info("Received shutdown signal")
        self.running = False

    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Shutting down worker process")
        # Cleanup resources, cancel tasks, etc.


async def main():
    """Entry point for the worker process."""
    # Setup logging
    setup_logging()

    # Create and start worker
    worker = WorkerProcess()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())

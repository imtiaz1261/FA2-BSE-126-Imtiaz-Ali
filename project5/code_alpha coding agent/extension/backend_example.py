"""
Code Alpha WebSocket Backend Server Example

This is a reference implementation showing how to integrate the VS Code extension
with the Code Alpha orchestrator. It demonstrates the complete WebSocket protocol.

Requirements:
    pip install websockets asyncio json
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Task execution states matching orchestrator"""
    PLANNING = "Planning"
    GENERATING = "Generating"
    TESTING = "Testing"
    FIXING = "Fixing"
    AWAITING_REVIEW = "AwaitingReview"
    COMPLETE = "Complete"
    FAILED = "Failed"
    IDLE = "Idle"


class WebSocketServer:
    """WebSocket server handling Code Alpha agent communication"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set = set()
        self.active_task: Optional[Dict] = None
        self.task_history: list = []

    async def start(self):
        """Start the WebSocket server"""
        async with asyncio.serve(self.handle_client, self.host, self.port):
            logger.info(f"🚀 WebSocket server running at ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket, path):
        """Handle a new client connection"""
        self.clients.add(websocket)
        logger.info(f"✅ Client connected. Total clients: {len(self.clients)}")

        try:
            # Send connection confirmation
            await websocket.send(json.dumps({
                "type": "connected",
                "payload": {
                    "sessionId": "session_" + str(id(websocket)),
                    "version": "1.0",
                    "features": [
                        "task_control",
                        "diff_review",
                        "spec_management",
                        "inline_edits",
                        "activity_logging"
                    ]
                }
            }))

            # Listen for client messages
            async for message in websocket:
                await self.handle_message(websocket, message)

        except asyncio.CancelledError:
            logger.info("Client disconnected (cancelled)")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            self.clients.remove(websocket)
            logger.info(f"❌ Client disconnected. Total clients: {len(self.clients)}")

    async def handle_message(self, websocket, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "control":
                await self.handle_control(websocket, data)
            elif msg_type == "review":
                await self.handle_review(websocket, data)
            elif msg_type == "specs":
                await self.handle_specs(websocket, data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            await self.send_error(websocket, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(websocket, str(e))

    async def handle_control(self, websocket, data: dict):
        """Handle control messages (pause, resume, stop)"""
        action = data.get("action")

        if action == "pause":
            await self.pause_task()
        elif action == "resume":
            await self.resume_task()
        elif action == "stop":
            await self.stop_task()
        else:
            await self.send_error(websocket, f"Unknown control action: {action}")

    async def handle_review(self, websocket, data: dict):
        """Handle review messages (approve, reject, request-changes)"""
        action = data.get("action")
        payload = data.get("payload", {})

        if action == "approve":
            await self.broadcast({
                "type": "diff_approved",
                "payload": {
                    "diffId": payload.get("diffId"),
                    "message": "Changes approved. Proceeding to next task."
                }
            })
            await self.simulate_task_progress()

        elif action == "reject":
            await self.broadcast({
                "type": "diff_rejected",
                "payload": {
                    "diffId": payload.get("diffId"),
                    "reason": payload.get("reason"),
                    "message": "Changes rejected. Reverting changes."
                }
            })

        elif action == "request-changes":
            await self.broadcast({
                "type": "changes_requested",
                "payload": {
                    "diffId": payload.get("diffId"),
                    "feedback": payload.get("feedback"),
                    "message": "Feedback recorded. Agent will refactor based on your input."
                }
            })

    async def handle_specs(self, websocket, data: dict):
        """Handle spec messages (update, regenerate, history)"""
        action = data.get("action")
        payload = data.get("payload", {})

        if action == "regenerate":
            await self.broadcast({
                "type": "spec_generation_started",
                "payload": {
                    "taskId": "spec_regen_" + str(datetime.now().timestamp()),
                    "message": f"Regenerating specs from {payload.get('from', 'requirements')}..."
                }
            })

            # Simulate regeneration
            await asyncio.sleep(2)
            await self.broadcast({
                "type": "spec_updated",
                "payload": {
                    "type": "requirements",
                    "version": 2,
                    "message": "Specifications updated successfully."
                }
            })

    async def pause_task(self):
        """Pause current task"""
        await self.broadcast({
            "type": "status_change",
            "payload": {
                "state": TaskState.AWAITING_REVIEW.value,
                "message": "Task paused by user",
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
        })

    async def resume_task(self):
        """Resume paused task"""
        await self.broadcast({
            "type": "status_change",
            "payload": {
                "state": TaskState.GENERATING.value,
                "message": "Task resumed",
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
        })
        await self.simulate_task_progress()

    async def stop_task(self):
        """Stop current task"""
        await self.broadcast({
            "type": "status_change",
            "payload": {
                "state": TaskState.FAILED.value,
                "message": "Task stopped by user",
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
        })

    async def simulate_task_progress(self):
        """Simulate task execution with edits and diffs"""
        task_id = f"task_{int(datetime.now().timestamp())}"
        self.active_task = {
            "id": task_id,
            "name": "Generate Authentication Module",
            "startTime": int(datetime.now().timestamp() * 1000),
            "logs": []
        }

        # Simulate different task states
        states = [
            (TaskState.PLANNING, "Planning implementation approach"),
            (TaskState.GENERATING, "Generating code files"),
            (TaskState.TESTING, "Running test suite"),
            (TaskState.FIXING, "Fixing test failures"),
            (TaskState.AWAITING_REVIEW, "Awaiting review"),
        ]

        for state, description in states:
            # Send status change
            await self.broadcast({
                "type": "status_change",
                "payload": {
                    "state": state.value,
                    "currentTask": task_id,
                    "details": description,
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
            })

            # Simulate edit
            if state == TaskState.GENERATING:
                await self.broadcast({
                    "type": "edit_start",
                    "payload": {
                        "filePath": "src/auth.py",
                        "operation": "create",
                        "description": "Creating authentication module"
                    }
                })

                await asyncio.sleep(1)

                await self.broadcast({
                    "type": "edit_end",
                    "payload": {
                        "filePath": "src/auth.py",
                        "success": True,
                        "linesChanged": 45
                    }
                })

                # Send diff for review
                await asyncio.sleep(0.5)
                await self.broadcast({
                    "type": "diff_ready",
                    "payload": {
                        "diffId": f"diff_{task_id}_1",
                        "filePath": "src/auth.py",
                        "oldContent": "",
                        "newContent": """# Authentication Module
import hashlib
from typing import Optional

class AuthManager:
    '''Manages user authentication'''
    
    def __init__(self):
        self.users = {}
    
    def register(self, username: str, password: str) -> bool:
        '''Register a new user'''
        if username in self.users:
            return False
        self.users[username] = self._hash_password(password)
        return True
    
    def authenticate(self, username: str, password: str) -> bool:
        '''Authenticate a user'''
        if username not in self.users:
            return False
        return self.users[username] == self._hash_password(password)
    
    @staticmethod
    def _hash_password(password: str) -> str:
        '''Hash a password using SHA-256'''
        return hashlib.sha256(password.encode()).hexdigest()
""",
                        "startLine": 0,
                        "endLine": 32,
                        "changeType": "creation",
                        "description": "Added authentication module with user registration and login"
                    }
                })

            # Send task update
            progress = int((states.index((state, description)) + 1) / len(states) * 100)
            await self.broadcast({
                "type": "task_update",
                "payload": {
                    "id": task_id,
                    "name": self.active_task["name"],
                    "state": state.value,
                    "progress": progress,
                    "startTime": self.active_task["startTime"],
                    "currentStep": description
                }
            })

            # Send log entry
            await self.broadcast({
                "type": "log",
                "payload": {
                    "taskId": task_id,
                    "level": "info",
                    "message": description,
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
            })

            # Wait between state transitions
            await asyncio.sleep(2)

        # Task complete
        await self.broadcast({
            "type": "task_update",
            "payload": {
                "id": task_id,
                "name": self.active_task["name"],
                "state": TaskState.COMPLETE.value,
                "progress": 100,
                "startTime": self.active_task["startTime"],
                "endTime": int(datetime.now().timestamp() * 1000),
                "summary": "Authentication module successfully generated and tested"
            }
        })

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        if not self.clients:
            return

        message_json = json.dumps(message)
        await asyncio.gather(
            *[client.send(message_json) for client in self.clients],
            return_exceptions=True
        )
        logger.debug(f"📤 Broadcast: {message.get('type')}")

    async def send_error(self, websocket, error_message: str):
        """Send error message to specific client"""
        await websocket.send(json.dumps({
            "type": "error",
            "payload": {
                "code": "SERVER_ERROR",
                "message": error_message,
                "severity": "error"
            }
        }))


async def main():
    """Main entry point"""
    server = WebSocketServer()

    # Optionally simulate a task immediately
    async def simulate_after_delay():
        await asyncio.sleep(5)
        logger.info("🎬 Starting simulated task...")
        await server.simulate_task_progress()

    # Start server and simulation
    task = asyncio.create_task(simulate_after_delay())

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        task.cancel()


if __name__ == "__main__":
    # Use websockets from Python 3.10+
    try:
        from websockets.server import serve
        asyncio.run(main())
    except ImportError:
        logger.error("websockets library not installed. Install with: pip install websockets")

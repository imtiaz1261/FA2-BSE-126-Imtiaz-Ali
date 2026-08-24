"""
WebSocket server for VS Code extension communication.

Handles real-time bidirectional communication with IDE.
"""

import json
import logging
import asyncio
from typing import Set, Callable, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from .models import ExtensionMessage, MessageType, ControlMessage, ControlCommand

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with IDE clients.
    
    Tracks active connections and broadcasts messages.
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.task_handlers: Dict[str, Callable] = {}
    
    async def connect(self, websocket: WebSocket) -> None:
        """Register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Active connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: ExtensionMessage) -> None:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: ExtensionMessage to broadcast
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return
        
        msg_dict = message.to_dict()
        msg_json = json.dumps(msg_dict)
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(msg_json)
            except Exception as e:
                logger.warning(f"Error sending message to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def send_to(self, websocket: WebSocket, message: ExtensionMessage) -> None:
        """
        Send message to specific client.
        
        Args:
            websocket: Target WebSocket connection
            message: ExtensionMessage to send
        """
        try:
            msg_dict = message.to_dict()
            msg_json = json.dumps(msg_dict)
            await websocket.send_text(msg_json)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            await self.disconnect(websocket)
    
    async def receive_message(self, websocket: WebSocket) -> Optional[ControlMessage]:
        """
        Receive and parse control message from client.
        
        Args:
            websocket: Client connection
        
        Returns:
            Parsed ControlMessage or None if error
        """
        try:
            data = await websocket.receive_text()
            msg_dict = json.loads(data)
            return ControlMessage.from_dict(msg_dict)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from client")
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None
    
    def register_handler(self, command: ControlCommand, handler: Callable) -> None:
        """
        Register handler for control command.
        
        Args:
            command: ControlCommand to handle
            handler: Async callable(task_id, reason) -> None
        """
        self.task_handlers[command.value] = handler
        logger.debug(f"Registered handler for command: {command.value}")
    
    async def handle_control_message(self, message: ControlMessage) -> bool:
        """
        Handle control message from client.
        
        Args:
            message: ControlMessage to process
        
        Returns:
            True if handled successfully
        """
        handler = self.task_handlers.get(message.command.value)
        if not handler:
            logger.warning(f"No handler for command: {message.command.value}")
            return False
        
        try:
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                await handler(message.task_id, message.reason)
            else:
                handler(message.task_id, message.reason)
            
            logger.debug(f"Handled command: {message.command.value}")
            return True
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return False


class ExtensionServer:
    """
    FastAPI-based server for IDE extension communication.
    
    Provides WebSocket endpoint and REST endpoints for extension integration.
    """
    
    def __init__(self, app: Optional[FastAPI] = None):
        self.app = app or FastAPI(
            title="Code Alpha Extension Server",
            description="Real-time IDE integration for Code Alpha agent",
            version="0.1.0",
        )
        self.manager = ConnectionManager()
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup WebSocket and HTTP routes."""
        
        @self.app.websocket("/ws/agent")
        async def websocket_endpoint(websocket: WebSocket):
            """Main WebSocket endpoint for IDE connection."""
            await self.manager.connect(websocket)
            
            try:
                # Keep connection alive and receive control messages
                while True:
                    # Receive message from client (blocking)
                    msg = await self.manager.receive_message(websocket)
                    
                    if msg:
                        # Handle control message
                        await self.manager.handle_control_message(msg)
            
            except WebSocketDisconnect:
                await self.manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await self.manager.disconnect(websocket)
        
        @self.app.get("/health/extension")
        async def extension_health():
            """Check extension server health."""
            return {
                "status": "healthy",
                "active_connections": len(self.manager.active_connections),
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        @self.app.get("/extension/status")
        async def get_extension_status():
            """Get current extension and connection status."""
            return {
                "connected": len(self.manager.active_connections) > 0,
                "connection_count": len(self.manager.active_connections),
                "handlers": list(self.manager.task_handlers.keys()),
            }
        
        @self.app.post("/extension/broadcast")
        async def broadcast_message(message: Dict[str, Any]):
            """
            Broadcast message to all connected clients.
            
            For testing and programmatic message sending.
            """
            try:
                ext_msg = ExtensionMessage(
                    type=MessageType(message.get('type', 'status_update')),
                    data=message.get('data', {}),
                )
                await self.manager.broadcast(ext_msg)
                return {"status": "success", "clients_reached": len(self.manager.active_connections)}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    async def send_status(
        self,
        task_id: str,
        status_info: Dict[str, Any]
    ) -> None:
        """
        Send status update to all connected clients.
        
        Args:
            task_id: Task identifier
            status_info: Status information dictionary
        """
        message = ExtensionMessage.status_update(
            task_id=task_id,
            status=status_info['status'],
            phase=status_info['phase'],
            progress=status_info.get('progress', 0),
            current_file=status_info.get('current_file'),
            current_line=status_info.get('current_line', 0),
            message=status_info.get('message', ''),
        )
        await self.manager.broadcast(message)
    
    async def send_log(self, task_id: str, line: str, level: str = "info") -> None:
        """
        Send log line to all connected clients.
        
        Args:
            task_id: Task identifier
            line: Log line content
            level: Log level (info, debug, warning, error)
        """
        message = ExtensionMessage.log_line(task_id, line, level)
        await self.manager.broadcast(message)
    
    async def send_file_edit(
        self,
        task_id: str,
        file_path: str,
        operation: str,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
        current_line: int = 0,
    ) -> None:
        """
        Send file edit notification to all clients.
        
        Args:
            task_id: Task identifier
            file_path: Path to file being edited
            operation: "create", "modify", or "delete"
            old_content: Original content (for modify/delete)
            new_content: New content (for create/modify)
            current_line: Current line being edited
        """
        from .models import FileEdit
        
        edit = FileEdit(
            file_path=file_path,
            operation=operation,
            old_content=old_content,
            new_content=new_content,
        )
        
        message = ExtensionMessage.file_edit(task_id, edit, current_line)
        await self.manager.broadcast(message)
    
    async def send_approval_required(
        self,
        task_id: str,
        reason: str,
        files_affected: List[str],
    ) -> None:
        """
        Send approval required notification.
        
        Args:
            task_id: Task identifier
            reason: Why approval is needed
            files_affected: List of affected files
        """
        message = ExtensionMessage.approval_required(task_id, reason, files_affected)
        await self.manager.broadcast(message)
    
    def register_control_handler(
        self,
        command: ControlCommand,
        handler: Callable
    ) -> None:
        """
        Register handler for control command from IDE.
        
        Args:
            command: ControlCommand to handle
            handler: Async callable(task_id, reason) -> None
        """
        self.manager.register_handler(command, handler)

"""WebSocket Manager for Real-Time Event Broadcasting.

Demonstrates:
- Persistent bi-directional WebSocket connections
- Multi-client subscription tracking
- Connection lifecycle management (connect, disconnect, broadcast, cleanup)
- Real-time event notifications on ticket changes and alerts
"""

import json
from typing import Any, Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from app.utils.logger import get_logger

logger = get_logger()


class ConnectionManager:
    """Singleton-style manager to broadcast events to all active WebSocket clients."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new client WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected. Total active connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected client from the subscriber pool."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total active connections: %d", len(self.active_connections))

    async def broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcasts an event message to all connected clients."""
        message = json.dumps({"event": event_type, "data": payload})
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as exc:
                logger.warning("Failed to send message to client, marking for cleanup: %s", exc)
                dead_connections.append(connection)

        # Clean up stale or dropped sockets
        for dead in dead_connections:
            self.disconnect(dead)


# Global singleton instance for app-wide event dispatch
ws_manager = ConnectionManager()

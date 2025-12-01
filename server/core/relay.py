"""WebSocket relay manager for WakeLink Cloud Server.

This module provides WebSocket connection management and message queuing
for offline devices in the WakeLink protocol v1.0.

Key concepts:
- Devices connect to /ws/{device_id}
- Clients connect to /ws/client/{client_id}
- When client sends command to device, relay tracks the pending response
- When device responds, relay forwards to the waiting client
"""

from fastapi import WebSocket
from typing import Dict, List, Any, Optional
import asyncio
import logging
import json

logger = logging.getLogger("wakelink_cloud")


class WebSocketManager:
    """Manages WebSocket connections and message relay for WakeLink.

    This class handles:
    - Active WebSocket connections for devices and clients
    - Message queuing for offline devices
    - Response routing from devices back to clients
    - Thread-safe operations using asyncio.Lock

    Attributes:
        connections: Dict mapping connection_id to WebSocket.
        queues: Dict mapping device_id to pending messages.
        pending_responses: Dict mapping device_id to client_id waiting for response.
        _lock: Asyncio lock for thread-safe access.
    """

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}  # connection_id -> WebSocket
        self.queues: Dict[str, List[Any]] = {}  # device_id -> pending messages
        self.pending_responses: Dict[str, str] = {}  # device_id -> client_id waiting
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, connection_id: str, already_accepted: bool = True):
        """Register a new WebSocket connection.

        Args:
            ws: The WebSocket connection object.
            connection_id: Unique identifier (device_id or client_xxx).
            already_accepted: If True, WebSocket was already accepted (default).
        """
        if not already_accepted:
            await ws.accept()
        async with self._lock:
            self.connections[connection_id] = ws
            queued = self.queues.get(connection_id, [])

        # Deliver any queued messages
        if queued:
            logger.info(f"Delivering {len(queued)} queued messages to {connection_id}")
            for msg in queued:
                try:
                    await ws.send_text(json.dumps(msg))
                except Exception:
                    logger.exception("Failed to send queued message")
                    break
            async with self._lock:
                self.queues.pop(connection_id, None)

        logger.info(f"WebSocket connected: {connection_id}")

    async def disconnect(self, connection_id: str):
        """Remove the WebSocket connection.

        Args:
            connection_id: The connection identifier.
        """
        async with self._lock:
            ws = self.connections.pop(connection_id, None)
            # Clean up any pending response associations
            for device_id, client_id in list(self.pending_responses.items()):
                if client_id == connection_id:
                    del self.pending_responses[device_id]
        
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        logger.info(f"WebSocket disconnected: {connection_id}")

    async def push(self, target_id: str, data: dict, sender_id: Optional[str] = None) -> bool:
        """Send data to a connected device/client.

        If target is connected, sends immediately. Otherwise queues for later.

        Args:
            target_id: Target device_id or client_id.
            data: The message data (outer JSON packet).
            sender_id: Optional sender connection_id for response tracking.

        Returns:
            bool: True if delivered immediately, False if queued.
        """
        async with self._lock:
            ws = self.connections.get(target_id)
            
            # Track pending response if client is waiting for device
            if sender_id and sender_id.startswith("client_"):
                self.pending_responses[target_id] = sender_id
                logger.debug(f"Tracking response: {target_id} -> {sender_id}")

        if ws:
            try:
                await ws.send_text(json.dumps(data))
                logger.info(f"Pushed message to {target_id}")
                return True
            except Exception:
                logger.exception(f"Failed to push to {target_id}, queuing")

        # Queue if delivery failed
        async with self._lock:
            q = self.queues.setdefault(target_id, [])
            q.append(data)
        logger.info(f"Message queued for {target_id}")
        return False

    async def push_response(self, device_id: str, data: dict) -> bool:
        """Forward device response to the waiting client.

        When a device sends a response, this finds the client that
        is waiting for it and forwards the encrypted response.

        Args:
            device_id: The device that sent the response.
            data: The response packet.

        Returns:
            bool: True if forwarded to client, False otherwise.
        """
        async with self._lock:
            client_id = self.pending_responses.pop(device_id, None)

        if not client_id:
            logger.debug(f"No client waiting for response from {device_id}")
            return False

        async with self._lock:
            ws = self.connections.get(client_id)

        if ws:
            try:
                await ws.send_text(json.dumps(data))
                logger.info(f"Forwarded response from {device_id} to {client_id}")
                return True
            except Exception:
                logger.exception(f"Failed to forward response to {client_id}")

        return False

    def get_connected_devices(self) -> List[str]:
        """Get list of connected device IDs (excluding clients)."""
        return [k for k in self.connections.keys() if not k.startswith("client_")]

    def is_connected(self, connection_id: str) -> bool:
        """Check if a connection is active."""
        return connection_id in self.connections

    def get_waiting_client(self, device_id: str) -> Optional[str]:
        """Get client_id waiting for response from device."""
        return self.pending_responses.get(device_id)


# Global instance
relay = WebSocketManager()
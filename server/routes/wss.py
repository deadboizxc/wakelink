"""WebSocket routes for WakeLink Cloud Server.

This module provides WebSocket endpoints for real-time bidirectional
communication with devices. Implements protocol v1.0 with transparent
relay of outer JSON packets.

The server acts as a blind relay:
- Validates API token from first JSON message (auth message)
- Does NOT decrypt the inner payload
- Forwards outer JSON {device_id, payload, signature, version} as-is

Authentication Protocol:
1. Client connects to /ws/{device_id} or /ws/client/{client_id}
2. Client sends auth message: {"type": "auth", "token": "<api_token>"}
3. Server validates token and sends welcome or error response
4. Normal packet exchange begins

Author: deadboizxc
Version: 1.0
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import validate_api_token
from core.models import Message, Device
from core.relay import relay

router = APIRouter(tags=["websocket"])
logger = logging.getLogger("wakelink_cloud")

# Authentication timeout in seconds
AUTH_TIMEOUT = 10.0


def _extract_token_from_headers(websocket: WebSocket) -> Optional[str]:
    """Extract API token from WebSocket headers (fallback for backwards compatibility).
    
    Checks:
    1. Authorization header (Bearer token)
    2. X-API-Token header
    
    Args:
        websocket: The WebSocket connection.
        
    Returns:
        The API token string or None if not found.
    """
    auth = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    
    return websocket.headers.get("x-api-token")


async def _wait_for_auth_message(
    websocket: WebSocket,
    timeout: float = AUTH_TIMEOUT
) -> tuple[bool, Optional[str], Optional[dict]]:
    """Wait for authentication message from client.
    
    Expected auth message format:
    {"type": "auth", "token": "<api_token>"}
    
    Args:
        websocket: The WebSocket connection.
        timeout: Maximum time to wait for auth message.
        
    Returns:
        Tuple of (success, token, first_data_message).
        first_data_message is returned if client sends a data packet instead of auth.
    """
    try:
        raw_data = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=timeout
        )
        
        try:
            message = json.loads(raw_data)
        except json.JSONDecodeError:
            return False, None, None
        
        # Check if this is an auth message
        if message.get("type") == "auth":
            token = message.get("token")
            return True, token, None
        
        # Not an auth message - might be a data packet (legacy client)
        # Return the message so it can be processed after header-based auth
        return False, None, message
        
    except asyncio.TimeoutError:
        return False, None, None
    except Exception:
        return False, None, None


async def _authenticate_websocket(
    websocket: WebSocket
) -> tuple[bool, Optional[object], Session, Optional[dict]]:
    """Authenticate WebSocket connection via JSON auth message.
    
    Authentication flow:
    1. Accept WebSocket connection
    2. Wait for auth message: {"type": "auth", "token": "..."}
    3. Validate token
    4. Send success/error response
    
    Also supports legacy header-based authentication for backwards compatibility.
    
    Args:
        websocket: The WebSocket connection.
        
    Returns:
        Tuple of (success, user, db_session, first_data_message).
        first_data_message is non-None if client sent data instead of auth (legacy).
    """
    db = next(get_db())
    await websocket.accept()
    
    # First, try to get token from headers (backwards compatibility)
    header_token = _extract_token_from_headers(websocket)
    
    # Wait for auth message
    auth_received, json_token, first_message = await _wait_for_auth_message(websocket)
    
    # Determine which token to use
    token = None
    if auth_received and json_token:
        # JSON auth takes priority
        token = json_token
        logger.debug("[WSS] Auth via JSON message")
    elif header_token:
        # Fall back to header-based auth (legacy)
        token = header_token
        logger.debug("[WSS] Auth via headers (legacy)")
    
    if not token:
        await websocket.send_json({
            "status": "error",
            "error": "AUTH_REQUIRED",
            "message": "Authentication required. Send: {\"type\": \"auth\", \"token\": \"<api_token>\"}"
        })
        await websocket.close(code=1008)
        return False, None, db, None
    
    user = validate_api_token(db, token)
    if not user:
        await websocket.send_json({
            "status": "error",
            "error": "INVALID_TOKEN",
            "message": "Invalid API token"
        })
        await websocket.close(code=1008)
        return False, None, db, None
    
    return True, user, db, first_message


@router.websocket("/ws/{device_id}")
async def websocket_device_endpoint(
    websocket: WebSocket,
    device_id: str
):
    """WebSocket endpoint for device (firmware) communication.
    
    Devices connect here to receive commands and send responses.
    The device_id in URL is used for routing messages.
    
    Authentication:
    After connecting, device must send auth message:
    {"type": "auth", "token": "<api_token>"}
    
    Protocol flow:
    1. Device connects to /ws/{device_id}
    2. Device sends auth message with API token
    3. Server validates and sends welcome message
    4. Client sends command to device via /ws/client/{client_id}
    5. Server relays command to device
    6. Device processes and sends response back
    7. Server relays response to waiting client
    
    Args:
        websocket: The WebSocket connection.
        device_id: Device identifier from URL path.
    """
    success, user, db, first_message = await _authenticate_websocket(websocket)
    
    if not success:
        return
    
    # Update device last_seen on connect
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if device:
        device.last_seen = datetime.now().astimezone()
        db.commit()
    
    await relay.connect(websocket, device_id)
    logger.info(f"[WSS] Device connected: {device_id} user={user.username}")
    
    try:
        await websocket.send_json({
            "type": "welcome",
            "status": "connected",
            "device_id": device_id,
            "protocol_version": "1.0",
            "message": "Device WebSocket connection established"
        })
        
        # Process first message if it was received during auth (legacy client)
        if first_message:
            message_data = first_message
            # Check for required fields (encrypted packet)
            required_fields = ["device_id", "payload", "signature", "version"]
            missing = [f for f in required_fields if f not in message_data]
            if not missing and message_data.get("version") == "1.0":
                # Process as response from device
                target_device_id = message_data.get("device_id")
                device = db.query(Device).filter(Device.device_id == target_device_id).first()
                if device:
                    device.last_seen = datetime.now().astimezone()
                    db.commit()
                
                outer_packet = {
                    "device_id": target_device_id,
                    "payload": message_data.get("payload"),
                    "signature": message_data.get("signature"),
                    "version": "1.0"
                }
                
                forwarded = await relay.push_response(device_id, outer_packet)
                if not forwarded:
                    msg = Message(
                        device_id=target_device_id,
                        device_token=device.device_token if device else None,
                        message_type="response",
                        message_data=message_data.get("payload", ""),
                        signature=message_data.get("signature", ""),
                        direction="to_client"
                    )
                    db.add(msg)
                    db.commit()
        
        while True:
            raw_data = await websocket.receive_text()
            
            try:
                message_data = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "status": "error",
                    "error": "INVALID_JSON",
                    "message": "Failed to parse JSON"
                })
                continue
            
            # Check for required fields (encrypted packet)
            required_fields = ["device_id", "payload", "signature", "version"]
            missing = [f for f in required_fields if f not in message_data]
            if missing:
                await websocket.send_json({
                    "status": "error",
                    "error": "INVALID_PACKET",
                    "message": f"Missing fields: {missing}"
                })
                continue
            
            if message_data.get("version") != "1.0":
                await websocket.send_json({
                    "status": "error",
                    "error": "UNSUPPORTED_VERSION",
                    "message": "Protocol version must be 1.0"
                })
                continue
            
            # Update device last_seen
            target_device_id = message_data.get("device_id")
            device = db.query(Device).filter(Device.device_id == target_device_id).first()
            if device:
                device.last_seen = datetime.now().astimezone()
                db.commit()
            
            # This is a RESPONSE from device (since device is sending it)
            # Forward to the client that's waiting
            outer_packet = {
                "device_id": target_device_id,
                "payload": message_data.get("payload"),
                "signature": message_data.get("signature"),
                "version": "1.0"
            }
            
            # Try to forward to waiting client
            forwarded = await relay.push_response(device_id, outer_packet)
            
            if forwarded:
                logger.debug(f"[WSS] Device {device_id} response forwarded to client")
            else:
                # No client waiting - store in DB for HTTP polling
                msg = Message(
                    device_id=target_device_id,
                    device_token=device.device_token if device else None,
                    message_type="response",
                    message_data=message_data.get("payload", ""),
                    signature=message_data.get("signature", ""),
                    direction="to_client"
                )
                db.add(msg)
                db.commit()
                logger.debug(f"[WSS] Device {device_id} response queued for HTTP")
    
    except WebSocketDisconnect:
        logger.info(f"[WSS] Device disconnected: {device_id}")
    except Exception as e:
        logger.error(f"[WSS] Error for device {device_id}: {e}")
    finally:
        await relay.disconnect(device_id)


@router.websocket("/ws/client/{client_id}")
async def websocket_client_endpoint(
    websocket: WebSocket,
    client_id: str
):
    """WebSocket endpoint for CLI/application clients.
    
    Clients connect here to send commands to devices.
    The server tracks which client is waiting for which device response.
    
    Authentication:
    After connecting, client must send auth message:
    {"type": "auth", "token": "<api_token>"}
    
    Protocol flow:
    1. Client connects to /ws/client/{client_id}
    2. Client sends auth message with API token
    3. Server validates and sends welcome message
    4. Client sends command packet with target device_id
    5. Server relays to device (if online) or queues
    6. Server sends ACK to client
    7. When device responds, server forwards to client
    
    Args:
        websocket: The WebSocket connection.
        client_id: Unique client identifier.
    """
    success, user, db, first_message = await _authenticate_websocket(websocket)
    
    if not success:
        return
    
    connection_id = f"client_{client_id}"
    await relay.connect(websocket, connection_id)
    logger.info(f"[WSS] Client connected: {client_id} user={user.username}")
    
    try:
        await websocket.send_json({
            "type": "welcome",
            "status": "connected",
            "client_id": client_id,
            "protocol_version": "1.0",
            "message": "Client WebSocket connection established"
        })
        
        # Process first message if it was received during auth (legacy client)
        pending_message = first_message
        
        while True:
            if pending_message:
                message_data = pending_message
                pending_message = None
            else:
                raw_data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(raw_data)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "status": "error",
                        "error": "INVALID_JSON"
                    })
                    continue
            
            required_fields = ["device_id", "payload", "signature", "version"]
            missing = [f for f in required_fields if f not in message_data]
            if missing:
                await websocket.send_json({
                    "status": "error",
                    "error": "INVALID_PACKET",
                    "message": f"Missing: {missing}"
                })
                continue
            
            if message_data.get("version") != "1.0":
                await websocket.send_json({
                    "status": "error",
                    "error": "UNSUPPORTED_VERSION"
                })
                continue
            
            target_device_id = message_data.get("device_id")
            
            # Update device last_seen
            device = db.query(Device).filter(Device.device_id == target_device_id).first()
            if device:
                device.last_seen = datetime.now().astimezone()
                db.commit()
            
            # Build command packet to send to device
            outer_packet = {
                "device_id": target_device_id,
                "payload": message_data.get("payload"),
                "signature": message_data.get("signature"),
                "version": "1.0"
            }
            
            # Push to device, tracking that this client wants the response
            delivered = await relay.push(target_device_id, outer_packet, sender_id=connection_id)
            
            if not delivered:
                # Device offline - store command in DB
                msg = Message(
                    device_id=target_device_id,
                    device_token=device.device_token if device else None,
                    message_type="command",
                    message_data=message_data.get("payload", ""),
                    signature=message_data.get("signature", ""),
                    direction="to_device"
                )
                db.add(msg)
                db.commit()
            
            # Send ACK to client
            await websocket.send_json({
                "status": "success",
                "device_id": target_device_id,
                "delivered": delivered,
                "queued": not delivered,
                "message": "Delivered to device" if delivered else "Device offline, queued"
            })
            
            logger.debug(f"[WSS] Client {client_id} -> {target_device_id} delivered={delivered}")
    
    except WebSocketDisconnect:
        logger.info(f"[WSS] Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"[WSS] Client error {client_id}: {e}")
    finally:
        await relay.disconnect(connection_id)
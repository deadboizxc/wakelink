"""API routes for WakeLink Cloud Server.

This module provides HTTP REST endpoints for device management and message relay.
All endpoints require API token authentication via Authorization header.

The server acts as a transparent relay - it never decrypts the payload,
only validates API tokens and forwards outer JSON packets.

Author: deadboizxc
Version: 1.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import validate_api_token, save_device, delete_device
from core.schemas import (
    PushMessage, PullRequest,
    DeviceCreate, DeviceRegisteredResponse, UserDevicesResponse,
    DeleteDeviceRequest, MessageResponse
)
from core.models import Message, Device, User
from core.relay import relay

router = APIRouter(prefix="/api", tags=["api"])
logger = logging.getLogger("wakelink_cloud")


async def get_api_token(
    authorization: Optional[str] = Header(None),
    x_api_token: Optional[str] = Header(None)
) -> Optional[str]:
    """Extract API token from request headers.

    Supports both 'Authorization: Bearer <token>' and 'X-API-Token' headers.

    Args:
        authorization: Authorization header value.
        x_api_token: X-API-Token header value.

    Returns:
        The extracted API token string, or None if not found.
    """
    if authorization and authorization.startswith("Bearer "):
        return authorization.replace("Bearer ", "")
    return x_api_token


async def validate_api_token_dependency(
    db: Session = Depends(get_db),
    api_token: Optional[str] = Depends(get_api_token)
) -> User:
    """Validate API token and return the associated user.

    Args:
        db: Database session.
        api_token: The API token to validate.

    Returns:
        The User object if token is valid.

    Raises:
        HTTPException: If token is invalid or missing.
    """
    if not api_token:
        raise HTTPException(status_code=401, detail="API token required")
    user = validate_api_token(db, api_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return user


def _is_device_online(last_seen: Optional[datetime]) -> bool:
    """Check if a device is considered online.

    A device is online if it was seen within the last 5 minutes.

    Args:
        last_seen: The last seen timestamp of the device.

    Returns:
        True if the device is online, False otherwise.
    """
    if not last_seen:
        return False
    try:
        return (datetime.now().astimezone() - last_seen) < timedelta(minutes=5)
    except Exception:
        return False


@router.get("/stats")
async def api_stats(db: Session = Depends(get_db)):
    """Get server statistics including device and user counts."""
    from datetime import datetime, timedelta
    
    five_min_ago = datetime.now().astimezone() - timedelta(minutes=5)
    online = db.query(Device).filter(Device.last_seen >= five_min_ago).count()
    total = db.query(Device).count()
    total_users = db.query(User).count()
    queues_to_device = db.query(Message).filter(Message.direction == 'to_device').count()
    queues_to_client = db.query(Message).filter(Message.direction == 'to_client').count()
    
    # WebSocket statistics
    ws_connections = len(relay.connections)
    
    return {
        "online_devices": online,
        "total_devices": total,
        "total_users": total_users,
        "queues_to_device": queues_to_device,
        "queues_to_client": queues_to_client,
        "total_queues": queues_to_device + queues_to_client,
        "websocket_connections": ws_connections,
        "server_time": datetime.now().isoformat(),
        "status": "running"
    }

@router.get("/health")
async def api_health():
    """Health check endpoint for monitoring services."""
    return {
        "status": "healthy",
        "service": "WakeLink Cloud Relay",
        "timestamp": datetime.now().isoformat(),
        "websockets": len(relay.connections)
    }

@router.post("/push", response_model=MessageResponse)
async def push_message(
    msg: PushMessage,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Send a message to a device.

    The device_id is specified in the request body. The server acts as a
    transparent relay and does not decrypt the payload.

    Args:
        msg: The push message containing device_id, payload, signature, version.
        db: Database session.
        user: Authenticated user.

    Returns:
        Response indicating success and delivery status.
    """
    # Update device last seen time
    device = db.query(Device).filter(Device.device_id == msg.device_id).first()
    if device:
        device.last_seen = datetime.now().astimezone()
        db.commit()
    
    # Save message to database for the device
    message = Message(
        device_id=msg.device_id,
        device_token=device.device_token if device else None,
        message_type="command" if msg.direction == "to_device" else "response",
        message_data=msg.payload,
        signature=msg.signature,
        direction=msg.direction
    )
    db.add(message)
    db.commit()
    
    # Try to deliver immediately via WebSocket if device is online
    delivered = False
    if device:
        delivered = await relay.push(msg.device_id, {
            "device_id": msg.device_id,
            "payload": msg.payload,
            "signature": msg.signature,
            "version": msg.version
        })
    
    return {
        "status": "ok",
        "device_id": msg.device_id,
        "delivered_via_ws": delivered
    }

@router.post("/pull", response_model=MessageResponse)
async def pull_messages(
    msg: PullRequest,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Retrieve pending messages for a device with optional long polling.

    The device_id is specified in the request body. Returns all queued
    messages for the device.
    
    Long polling: If wait > 0, server will hold the connection for up to
    'wait' seconds until messages arrive, enabling near-instant responses.

    Args:
        msg: The pull request containing device_id and optional wait time.
        db: Database session.
        user: Authenticated user.

    Returns:
        Response with list of messages for the device.
    """
    # Update device last seen (always) and poll count (only for real polls, not heartbeats)
    device = db.query(Device).filter(Device.device_id == msg.device_id).first()
    if device:
        device.last_seen = datetime.now().astimezone()
        db.commit()
    
    # Long polling support
    wait_time = min(msg.wait or 0, 30)  # Max 30 seconds
    start_time = datetime.now()
    poll_interval = 0.1  # 100ms between DB checks
    
    messages = []
    
    while True:
        # Get all messages for the device based on requested direction
        messages = db.query(Message).filter(
            Message.device_id == msg.device_id,
            Message.direction == msg.direction
        ).order_by(Message.timestamp).all()
        
        # If we have messages or not long polling, return immediately
        if messages or wait_time == 0:
            break
        
        # Check if we've waited long enough
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed >= wait_time:
            break
        
        # Wait a bit before checking again
        await asyncio.sleep(poll_interval)
        
        # Refresh DB session to see new messages
        db.expire_all()
    
    # Only increment poll_count if there were actual messages (not just heartbeat)
    if device and len(messages) > 0:
        device.poll_count += 1
        db.commit()
    
    result = []
    for msg_obj in messages:
        result.append({
            "device_id": msg_obj.device_id,
            "message_type": msg_obj.message_type,
            "packet": msg_obj.message_data,
            "payload": msg_obj.message_data,
            "signature": msg_obj.signature or "",
            "direction": msg_obj.direction,
            "timestamp": msg_obj.timestamp.isoformat() if msg_obj.timestamp else None
        })
    
    # Delete delivered messages
    for message in messages:
        db.delete(message)
    db.commit()
    
    return {
        "status": "ok",
        "device_id": msg.device_id,
        "messages": result,
        "count": len(result)
    }

# =============================
# Client endpoints (API token in headers)
# =============================

@router.post("/register_device", response_model=DeviceRegisteredResponse)
async def api_register_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Register a new device for the authenticated user.

    API token is passed in Authorization header.

    Args:
        device_data: Device creation data.
        db: Database session.
        user: Authenticated user.

    Returns:
        Device registration response.
    """
    try:
        device = save_device(db, user.id, device_data.device_id, device_data.device_data or {})
        return {
            "status": "device_registered",
            "device_id": device.device_id,
            "device_token": device.device_token,
            "mode": "cloud"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/delete_device", response_model=dict)
async def api_delete_device(
    request: DeleteDeviceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Delete a device for the authenticated user.

    API token in headers, device_id in request body.

    Args:
        request: Delete device request with device_id.
        db: Database session.
        user: Authenticated user.

    Returns:
        Deletion confirmation.
    """
    success, message = delete_device(db, user.api_token, request.device_id)
    if success:
        return {
            "status": "device_deleted",
            "message": message
        }
    else:
        raise HTTPException(status_code=404, detail=message)

@router.get("/devices", response_model=UserDevicesResponse)
async def api_devices(
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Get list of devices for the authenticated user.

    API token passed in headers.

    Args:
        db: Database session.
        user: Authenticated user.

    Returns:
        List of user's devices with status information.
    """
    devices = db.query(Device).filter(Device.user_id == user.id).all()
    devices_list = []
    
    for device in devices:
        online = _is_device_online(device.last_seen)
        devices_list.append({
            "device_id": device.device_id,
            "cloud": device.cloud,
            "online": online,
            "last_seen": device.last_seen,
            "poll_count": device.poll_count,
            "added": device.added
        })

    return {
        "user": user.username,
        "plan": user.plan,
        "devices_limit": user.devices_limit,
        "devices_count": len(devices_list),
        "devices": devices_list
    }


# New CLI-compatible endpoints: device create/get/update/delete

@router.post("/device/create")
async def api_device_create(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Create a device. Expects device_id and device_token in body."""
    device_id = payload.get("device_id")
    device_token = payload.get("device_token")
    if not device_id or not device_token:
        raise HTTPException(status_code=400, detail="device_id and device_token required")

    try:
        device = save_device(db, user.id, device_id, {"device_token": device_token})
        return {"status": "ok", "device_id": device_id, "device_token": device_token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/device/")
async def api_device_get(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Get device information by device_id."""
    device = db.query(Device).filter(Device.device_id == device_id, Device.user_id == user.id).first()
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return {
        "device_id": device.device_id,
        "cloud": getattr(device, 'cloud', False),
        "last_seen": getattr(device, 'last_seen', None)
    }

@router.put("/device/update")
async def api_device_update(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Update device (partial). Expects device_id, device_token, and optionally signature/version."""
    device_id = payload.get("device_id")
    device_token = payload.get("device_token")
    if not device_id or not device_token:
        raise HTTPException(status_code=400, detail="device_id and device_token required")

    device = db.query(Device).filter(Device.device_id == device_id, Device.user_id == user.id).first()
    if not device:
        raise HTTPException(status_code=404, detail="device not found")

    # Update token/version/metadata
    device.device_token = device_token
    if 'version' in payload:
        device.version = payload.get('version')
    db.commit()

    return {"status": "ok", "device_id": device_id}

@router.delete("/device/delete")
async def api_device_delete(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(validate_api_token_dependency)
):
    """Delete device by device_id and device_token."""
    device_id = payload.get("device_id")
    device_token = payload.get("device_token")
    if not device_id or not device_token:
        raise HTTPException(status_code=400, detail="device_id and device_token required")

    device = db.query(Device).filter(Device.device_id == device_id, Device.user_id == user.id).first()
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    db.delete(device)
    db.commit()
    return {"status": "device_deleted", "device_id": device_id}
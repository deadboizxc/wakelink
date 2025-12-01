"""Admin routes for WakeLink Cloud Server.

This module provides web-based administration endpoints for the WakeLink
Cloud Server dashboard. Implements user session management via cookies
and renders HTML templates for device management interface.

The dashboard displays:
- User's registered devices with online/offline status
- System-wide statistics (total devices, users, message queues)
- Real-time device information and API tokens

Authentication:
    Uses cookie-based sessions with user_id stored in browser cookies.
    Redirects to /login if session is invalid or expired.

Author: deadboizxc
Version: 1.0
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.utils import is_device_online
from core.models import User, Device, Message
from fastapi.templating import Jinja2Templates
from datetime import datetime
from core.config import settings
from core.utils import get_dynamic_base_url

router = APIRouter(prefix="", tags=["admin"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Render the user dashboard page.
    
    Displays comprehensive device management interface with:
    - List of user's registered devices
    - Online/offline status indicators
    - System-wide statistics
    - API token for programmatic access
    
    Authentication:
        Requires valid user_id cookie. Redirects to /login if missing.
    
    Args:
        request: The FastAPI request object containing cookies.
        db: Database session dependency.
    
    Returns:
        HTMLResponse: Rendered dashboard.html template with context data.
        RedirectResponse: Redirect to /login if authentication fails.
    
    Template Context:
        user: Dict with username, plan, devices_count, devices_limit, devices list.
        api_token: User's API token for REST/WebSocket authentication.
        online_count: Number of user's devices currently online.
        system_stats: Server-wide statistics dict.
        server_time: Current server timestamp.
        base_url: Dynamic base URL for API endpoints.
    """
    # Extract user_id from session cookie for authentication
    user_id = request.cookies.get("user_id")
    if not user_id:
        # No session cookie - redirect to login page
        return RedirectResponse(url="/login")
    
    try:
        # Validate user exists in database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            # Invalid user_id in cookie - session expired or tampered
            return RedirectResponse(url="/login")
        
        # Fetch all devices registered to this user
        devices = db.query(Device).filter(Device.user_id == int(user_id)).all()

        # Count devices that have been seen within the last 5 minutes or have active WSS
        online_count = sum(1 for device in devices if is_device_online(device.last_seen, device.device_id))

        # Calculate system-wide statistics for admin overview
        from datetime import timedelta
        from core.relay import relay
        five_min_ago = datetime.now().astimezone() - timedelta(minutes=5)

        # Count online devices: WSS connected OR seen in last 5 min
        wss_connected = set(relay.get_connected_devices())
        http_online = set(d.device_id for d in db.query(Device).filter(Device.last_seen >= five_min_ago).all())
        total_online = len(wss_connected | http_online)

        # Aggregate system statistics across all users/devices
        # Used for admin dashboard overview panel
        system_stats = {
            "online_devices": total_online,  # Devices with active WSS or seen in last 5 min
            "wss_connections": len(wss_connected),  # Active WebSocket connections
            "total_devices": db.query(Device).count(),  # All registered devices
            "total_users": db.query(User).count(),  # Total registered users
            "queues_to_device": db.query(Message).filter(Message.direction == 'to_device').count(),  # Pending commands
            "queues_to_client": db.query(Message).filter(Message.direction == 'to_client').count(),  # Pending responses
        }

        # Prepare user data structure for Jinja2 template rendering
        user_data = {
            "username": user.username,
            "plan": user.plan,
            "devices_count": len(devices),
            "devices_limit": user.devices_limit,
            "devices": []
        }

        # Build device list with computed online status for each device
        for device in devices:
            user_data["devices"].append({
                "device_id": device.device_id,  # Unique device identifier (e.g., WL123ABC)
                "device_token": device.device_token,  # Secret token for ChaCha20/HMAC crypto
                "online": is_device_online(device.last_seen, device.device_id),  # WSS connected or seen recently
                "last_seen": device.last_seen,  # Last communication timestamp
                "poll_count": device.poll_count,  # Number of pull requests from device
                "added": device.added  # Device registration timestamp
            })

        # Compute base URL from request headers (handles proxy/reverse proxy scenarios)
        # Used for generating correct API endpoint URLs in the dashboard
        base_url = get_dynamic_base_url(request)

        
        # Render dashboard template with all context variables
        return templates.TemplateResponse("dashboard.html", {
            "request": request,  # Required by Jinja2Templates
            "user": user_data,  # User profile and device list
            "api_token": user.api_token,  # For displaying in dashboard UI
            "online_count": online_count,  # User's online devices count
            "system_stats": system_stats,  # Server-wide statistics
            "server_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Display timestamp
            "base_url": base_url  # For API endpoint references
        })
        
    except Exception as e:
        # Log error and redirect to login on any exception
        # This catches database errors, type conversion errors, etc.
        print(f"Dashboard error: {e}")
        return RedirectResponse(url="/login")


@router.post("/dashboard/delete_device")
async def dashboard_delete_device(request: Request, db: Session = Depends(get_db)):
    """Delete a device via dashboard (session-based authentication).
    
    Uses cookie-based session instead of API token for authentication.
    This endpoint is called from the dashboard JavaScript.
    
    Args:
        request: The FastAPI request containing cookies and JSON body.
        db: Database session dependency.
    
    Returns:
        JSONResponse: Success or error message.
    """
    # Extract user_id from session cookie
    user_id = request.cookies.get("user_id")
    if not user_id:
        return JSONResponse(
            status_code=401, 
            content={"detail": "Not authenticated"}
        )
    
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            return JSONResponse(
                status_code=401, 
                content={"detail": "Invalid session"}
            )
        
        # Parse request body
        body = await request.json()
        device_id = body.get("device_id")
        
        if not device_id:
            return JSONResponse(
                status_code=400, 
                content={"detail": "device_id required"}
            )
        
        # Find and verify device belongs to user
        device = db.query(Device).filter(
            Device.device_id == device_id,
            Device.user_id == user.id
        ).first()
        
        if not device:
            return JSONResponse(
                status_code=404, 
                content={"detail": "Device not found or access denied"}
            )
        
        # Delete the device
        device_id = device.device_id
        db.delete(device)
        db.commit()
        
        return JSONResponse(content={
            "status": "ok",
            "message": f"Device {device_id} deleted successfully"
        })
        
    except Exception as e:
        print(f"Delete device error: {e}")
        return JSONResponse(
            status_code=500, 
            content={"detail": str(e)}
        )
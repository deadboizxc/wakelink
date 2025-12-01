"""Home routes for WakeLink Cloud Server.

This module provides public-facing endpoints for the WakeLink Cloud Server
including the landing page and server status/test endpoints.

Endpoints:
    GET /: Landing page with server information
    GET /test: Debug endpoint showing server configuration and URLs

These endpoints do not require authentication and are suitable for:
- Health monitoring and service discovery
- Initial user onboarding and documentation
- Debug and troubleshooting purposes

Author: deadboizxc
Version: 1.0
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from core.utils import get_dynamic_base_url, get_stored_base_url
from core.config import settings
from core.database import get_db

router = APIRouter(prefix="", tags=["home"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Render the WakeLink Cloud Server landing page.
    
    Public endpoint displaying server information, documentation links,
    and quick start guides for new users.
    
    Args:
        request: The FastAPI request object.
        db: Database session dependency.
    
    Returns:
        HTMLResponse: Rendered home.html template with server context.
    
    Template Context:
        request: FastAPI request (required by Jinja2Templates).
        database_file: Path to SQLite database file (for debug info).
        base_url: Dynamically computed base URL for API references.
    """
    # Compute base URL from request headers
    # Handles reverse proxy scenarios (X-Forwarded-Proto, X-Forwarded-Host)
    base_url = get_dynamic_base_url(request)
    # Alternative: Use URL stored in database settings
    # base_url = get_stored_base_url(db)

    return templates.TemplateResponse("home.html", {
        "request": request,  # Required by Jinja2Templates
        "database_file": settings.DATABASE_FILE,  # Display current DB path
        "base_url": base_url  # For API endpoint documentation
    })


@router.get("/test")
async def test_endpoint(request: Request, db: Session = Depends(get_db)):
    """Debug endpoint for server configuration testing.
    
    Returns server status and URL configuration information.
    Useful for debugging proxy configurations and verifying
    that URL detection is working correctly.
    
    Args:
        request: The FastAPI request object.
        db: Database session dependency.
    
    Returns:
        dict: JSON response containing:
            - message: Server status message
            - base_url: Currently computed base URL
            - dynamic_url: URL computed from request headers
            - stored_url: URL stored in database (if any)
            - endpoints: Dict of common API endpoint URLs
    
    Note:
        This endpoint is intended for development/debugging.
        Consider disabling or protecting in production.
    """
    # Get dynamic base URL from request headers
    base_url = get_dynamic_base_url(request)
    
    return {
        "message": "WakeLink server is running",
        "base_url": base_url,  # Primary URL for API access
        "dynamic_url": get_dynamic_base_url(request),  # Computed from request
        "stored_url": get_stored_base_url(db),  # From database settings
        "endpoints": {
            # Common API endpoints for quick reference
            "health": f"{base_url}/api/health",  # Health check
            "stats": f"{base_url}/api/stats",  # Server statistics
            "devices": f"{base_url}/api/devices"  # Device management
        }
    }
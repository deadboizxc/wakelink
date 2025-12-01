from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session

from .config import settings
from .models import ServerConfig
from .relay import relay

def is_device_online(last_seen: Optional[datetime], device_id: Optional[str] = None) -> bool:
    """Check if device is online.
    
    A device is considered online if:
    1. It has an active WSS connection, OR
    2. It was seen within the last 5 minutes (HTTP polling)
    
    Args:
        last_seen: Last seen timestamp from database.
        device_id: Optional device ID to check WSS connection.
    
    Returns:
        True if device is online, False otherwise.
    """
    # Check if device has active WSS connection
    if device_id and relay.is_connected(device_id):
        return True
    
    # Fallback to last_seen check (HTTP polling)
    if not last_seen:
        return False
    try:
        now = datetime.now().astimezone()
        # Handle timezone-naive last_seen by assuming UTC
        if last_seen.tzinfo is None:
            from datetime import timezone
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        
        diff = now - last_seen
        return diff < timedelta(minutes=5)
    except Exception as e:
        print(f"[ONLINE CHECK] Error: {e}, last_seen={last_seen}")
        return False

def get_dynamic_base_url(request: Request) -> str:
    """Dynamically determines full base_url with protocol"""
    scheme = request.headers.get('x-forwarded-proto', request.url.scheme)
    host = request.headers.get('x-forwarded-host', request.headers.get('host', f'localhost:{settings.CLOUD_PORT}'))
    return f"{scheme}://{host}"

def get_stored_base_url(db: Session) -> str:
    """Gets base_url from database"""
    config = db.query(ServerConfig).filter(ServerConfig.key == 'base_url').first()
    return config.value if config else f"http://localhost:{settings.CLOUD_PORT}"

def update_base_url(db: Session, new_url: str) -> bool:
    """Updates base_url in database"""
    try:
        config = db.query(ServerConfig).filter(ServerConfig.key == 'base_url').first()
        if config:
            config.value = new_url
            config.updated_at = datetime.now().astimezone()
        else:
            db.add(ServerConfig(key='base_url', value=new_url))
        db.commit()
        return True
    except Exception as e:
        from . import logger
        logger.error(f"Failed to update base_url: {e}")
        return False
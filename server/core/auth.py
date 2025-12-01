import hashlib
import secrets
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Tuple, Dict, Any

from .models import User, Device

def hash_password(password: str) -> str:
    """Password hashing SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(length: int = 32) -> str:
    """Generate secure token"""
    return secrets.token_hex(length)

def validate_api_token(db: Session, api_token: str) -> Optional[User]:
    return db.query(User).filter(User.api_token == api_token).first()

def validate_device_token(db: Session, device_token: str) -> Optional[Device]:
    return db.query(Device).filter(Device.device_token == device_token).first()

def create_user(db: Session, user_data) -> Tuple[Optional[User], Optional[str]]:
    """Create user"""
    if db.query(User).filter(User.username == user_data.username).first():
        return None, "User already exists"

    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        api_token=generate_token(),
        plan='basic',
        devices_limit=5
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, None

def authenticate_user(db: Session, login_data) -> Optional[User]:
    """User authentication"""
    password_hash = hash_password(login_data.password)
    return db.query(User).filter(
        User.username == login_data.username,
        User.password_hash == password_hash
    ).first()

def save_device(db: Session, user_id: int, device_id: str, device_data: Dict[str, Any]) -> Device:
    """Register or update device"""
    from datetime import datetime
    
    # Check limit
    device_count = db.query(Device).filter(Device.user_id == user_id).count()
    user = db.query(User).filter(User.id == user_id).first()
    if user and device_count >= user.devices_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Device limit: maximum {user.devices_limit}"
        )

    device_token = device_data.get('device_token') or generate_token(16)
    cloud = True
    now = datetime.now().astimezone()

    # Check for existing device
    existing = db.query(Device).filter(
        Device.device_id == device_id,
        Device.user_id == user_id
    ).first()

    if existing:
        existing.device_token = device_token
        existing.cloud = cloud
        existing.last_seen = now
        device = existing
    else:
        device = Device(
            device_id=device_id,
            user_id=user_id,
            device_token=device_token,
            cloud=cloud,
            added=now,
            last_seen=now
        )
        db.add(device)

    db.commit()
    db.refresh(device)
    return device

def delete_device(db: Session, api_token: str, device_id: str) -> Tuple[bool, str]:
    """Delete device by device_id"""
    from .models import Message

    user = validate_api_token(db, api_token)
    if not user:
        return False, "Invalid API token"

    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.user_id == user.id
    ).first()

    if not device:
        return False, "Device not found or access denied"

    # Delete all device messages
    db.query(Message).filter(Message.device_id == device_id).delete()
    db.delete(device)
    db.commit()

    return True, f"Device {device_id} deleted"
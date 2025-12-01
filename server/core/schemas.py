from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

# Authentication
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# Devices
class DeviceCreate(BaseModel):
    device_id: str
    device_data: Optional[Dict[str, Any]] = None

class DeleteDeviceRequest(BaseModel):
    device_id: str

class DeviceInfo(BaseModel):
    device_id: str
    cloud: bool
    online: bool
    last_seen: Optional[datetime]
    poll_count: int
    added: Optional[datetime]  # Can be None if not set

# Messages (new format)
class PushMessage(BaseModel):
    device_id: str
    payload: str
    signature: str
    version: str = "1.0"
    direction: str = "to_device"  # "to_device" from client, "to_client" from device

class PullRequest(BaseModel):
    device_id: str
    # payload and signature are optional for pull - client just wants to fetch messages
    payload: Optional[str] = None
    signature: Optional[str] = None
    version: str = "1.0"
    direction: str = "to_client"  # "to_device" for device pull, "to_client" for client pull
    wait: Optional[int] = 0  # Long polling: wait up to N seconds for messages (0 = immediate)

class PullResponse(BaseModel):
    messages: List[Dict[str, str]]
    count: int

# API responses
class DeviceRegisteredResponse(BaseModel):
    status: str
    device_id: str
    device_token: str
    mode: str

class UserDevicesResponse(BaseModel):
    user: str
    plan: str
    devices_limit: int
    devices_count: int
    devices: List[DeviceInfo]

class MessageResponse(BaseModel):
    status: str
    device_id: str
    delivered_via_ws: bool = False
    messages: Optional[List[Dict]] = None
    count: Optional[int] = 0
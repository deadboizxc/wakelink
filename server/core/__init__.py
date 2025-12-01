import logging
from .config import settings
from .database import init_db, get_db, SessionLocal
from .models import Base, User, Device, Message, ServerConfig
from .auth import hash_password, generate_token, validate_api_token, validate_device_token
from .utils import is_device_online, get_dynamic_base_url, get_stored_base_url, update_base_url
from .cleanup import cleanup_old_messages, start_cleanup_thread

# Create logger, but do NOT configure basicConfig
logger = logging.getLogger("wakelink_cloud")

__all__ = [
    'settings',
    'init_db', 'get_db', 'SessionLocal',
    'Base', 'User', 'Device', 'Message', 'ServerConfig',
    'hash_password', 'generate_token', 'validate_api_token', 'validate_device_token',
    'is_device_online', 'get_dynamic_base_url', 'get_stored_base_url', 'update_base_url',
    'cleanup_old_messages', 'start_cleanup_thread', 'logger'
]
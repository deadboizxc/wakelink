from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    api_token = Column(String, unique=True, index=True)
    plan = Column(String, default='base')
    devices_limit = Column(Integer, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Device(Base):
    __tablename__ = "devices"
    
    device_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    device_token = Column(String, unique=True, index=True)
    cloud = Column(Boolean, default=True)
    added = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    poll_count = Column(Integer, default=0)
    last_counter = Column(Integer, default=0)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    device_token = Column(String, ForeignKey('devices.device_token'))
    device_id = Column(String, index=True)
    message_type = Column(String, default="command")
    message_data = Column(Text)
    signature = Column(String, nullable=True)  # Added for storing HMAC signature
    direction = Column(String)  # "to_device" | "to_client"
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ServerConfig(Base):
    __tablename__ = "server_config"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
"""Device Manager for WakeLink Client.

This module provides persistent storage and management of WakeLink device
configurations. Devices are stored in a JSON file (default: ~/.wakelink/devices.json)
and can be referenced by friendly names in CLI commands.

Device Storage Format:
    {
        "device_name": {
            "token": "device_secret_token",
            "ip": "192.168.1.50",
            "port": 99,
            "cloud": false,
            "device_id": "WL123ABC",
            "api_token": "api_key_for_cloud",
            "http_url": "https://wakelink.deadboizxc.org",
            "wss_url": "wss://wakelink.deadboizxc.org",
            "protocol": "http",
            "added": 1234567890.0
        }
    }

Author: deadboizxc
Version: 1.0
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# Default cloud server configuration
DEFAULT_HTTP_URL = "https://wakelink.deadboizxc.org"
DEFAULT_WSS_URL = "wss://wakelink.deadboizxc.org"
DEFAULT_PROTOCOL = "http"
DEFAULT_PORT = 99


class DeviceManager:
    """Manager for WakeLink device configurations.
    
    Provides CRUD operations for device records stored in a local JSON file.
    Supports both local TCP devices and cloud-registered devices.
    
    Attributes:
        file: Path to the devices JSON file.
        devices: Dict mapping device names to their configurations.
    
    File Location:
        Default: ~/.wakelink/devices.json
        The directory is created automatically if it doesn't exist.
    """

    def __init__(self, file: str = "~/.wakelink/devices.json"):
        """Initialize device manager with storage file path.
        
        Args:
            file: Path to JSON storage file. Supports ~ expansion.
        """
        self.file = Path(file).expanduser()
        self.devices: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        """Load devices from JSON file.
        
        Returns:
            Dict of device configurations, or empty dict if file doesn't exist.
        """
        if not self.file.exists():
            return {}
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load devices: {e}")
            return {}

    def _save(self) -> None:
        """Persist devices to JSON file.
        
        Creates parent directories if they don't exist.
        """
        # Ensure directory exists
        self.file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.devices, f, indent=2)
        except Exception as e:
            print(f"Failed to save devices: {e}")

    def add(self, name: str, ip: str = None, token: str = None, api_token: str = None, 
            http_url: str = None, wss_url: str = None, **kwargs) -> None:
        """Add or update a device configuration.
        
        Args:
            name: Friendly name for the device (used in CLI).
            ip: Device IP address (required for TCP mode).
            token: Device secret token for encryption (min 32 chars).
            api_token: API token for cloud authentication.
            http_url: HTTP URL for cloud transport (https://...).
            wss_url: WSS URL for WebSocket transport (wss://...).
            **kwargs: Additional options:
                - port: TCP port (default 99)
                - cloud: True for cloud mode
                - device_id: Device identifier for cloud
                - protocol: Transport protocol ('http' or 'wss')
        """
        # Build device data structure
        device_data = {
            "token": token,
            "port": kwargs.get("port", DEFAULT_PORT),
            "cloud": kwargs.get("cloud", False),
            "device_id": kwargs.get("device_id", name),
            "added": time.time()  # Timestamp for tracking
        }
        
        # Merge with existing device data (preserve fields not explicitly set)
        existing = self.devices.get(name, {})
        if existing:
            # Preserve old values if new ones not provided
            if not ip and existing.get("ip"):
                device_data["ip"] = existing["ip"]
            if not token and existing.get("token"):
                device_data["token"] = existing["token"]
            if not api_token and existing.get("api_token"):
                device_data["api_token"] = existing["api_token"]
            if not http_url and existing.get("http_url"):
                device_data["http_url"] = existing["http_url"]
            if not wss_url and existing.get("wss_url"):
                device_data["wss_url"] = existing["wss_url"]
            if not kwargs.get("protocol") and existing.get("protocol"):
                device_data["protocol"] = existing["protocol"]
            # Preserve original added timestamp
            if existing.get("added"):
                device_data["added"] = existing["added"]
        
        # Store URLs for cloud transport (use defaults for cloud devices)
        if http_url:
            device_data["http_url"] = http_url
        elif device_data["cloud"] and not existing.get("http_url"):
            device_data["http_url"] = DEFAULT_HTTP_URL
            
        if wss_url:
            device_data["wss_url"] = wss_url
        elif device_data["cloud"] and not existing.get("wss_url"):
            device_data["wss_url"] = DEFAULT_WSS_URL
        
        # Store protocol preference (use default for cloud devices)
        if kwargs.get("protocol"):
            device_data["protocol"] = kwargs["protocol"]
        elif device_data["cloud"] and not existing.get("protocol"):
            device_data["protocol"] = DEFAULT_PROTOCOL

        if device_data["cloud"] or http_url or wss_url:
            # Cloud/WSS device configuration
            if api_token:
                device_data["api_token"] = api_token
            if kwargs.get("token"):
                device_data["token"] = kwargs["token"]
            # Preserve IP for reference even in cloud mode
            if ip:
                device_data["ip"] = ip
        else:
            # Local TCP device - IP is required
            if ip:
                device_data["ip"] = ip

        self.devices[name] = device_data
        self._save()

    def remove(self, name: str) -> None:
        """Remove a device from configuration.
        
        Args:
            name: Device name to remove.
        """
        if name in self.devices:
            del self.devices[name]
            self._save()

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get device configuration by name.
        
        Args:
            name: Device name to look up.
            
        Returns:
            Device config dict or None if not found.
        """
        return self.devices.get(name)

    def list_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get all device configurations.
        
        Returns:
            Copy of the devices dict (safe for iteration).
        """
        return self.devices.copy()

    # =============================
    # Additional Convenience Methods
    # =============================
    
    def exists(self, name: str) -> bool:
        """Check if a device exists in configuration.
        
        Args:
            name: Device name to check.
            
        Returns:
            True if device exists, False otherwise.
        """
        return name in self.devices

    def get_device_names(self) -> List[str]:
        """Get list of all configured device names.
        
        Returns:
            List of device name strings.
        """
        return list(self.devices.keys())

    def update(self, name: str, **kwargs) -> bool:
        """Update specific fields of an existing device.
        
        Args:
            name: Device name to update.
            **kwargs: Fields to update with new values.
            
        Returns:
            True if device was updated, False if not found.
        """
        if name not in self.devices:
            return False
        
        for key, value in kwargs.items():
            self.devices[name][key] = value
        
        self._save()
        return True

    def clear(self) -> None:
        """Remove all devices from configuration.
        
        Warning: This permanently deletes all device data.
        """
        self.devices.clear()
        self._save()

    def count(self) -> int:
        """Get the number of configured devices.
        
        Returns:
            Number of devices in configuration.
        """
        return len(self.devices)
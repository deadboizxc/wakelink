"""WakeLink Protocol Commands Implementation.

This module provides the concrete implementation of WakeLink commands
using the protocol v1.0 packet format. Commands are transport-agnostic
and work with any handler (TCP, Cloud, WSS).

All commands:
1. Create encrypted packets via the handler's send_command()
2. Receive encrypted responses
3. Return decrypted result dictionaries

Command Mapping:
    ping          -> "ping"          : Test connectivity
    wake          -> "wake"          : Wake-on-LAN (requires MAC)
    info          -> "info"          : Device information
    restart       -> "restart"       : Restart device
    ota_start     -> "ota_start"     : Enable OTA mode
    open_setup    -> "open_setup"    : Configuration mode
    web_control   -> action: enable/disable/status
    cloud_control -> action: enable/disable/status
    crypto_info   -> "crypto_info"   : Encryption status
    update_token  -> "update_token"  : Refresh device token

Author: deadboizxc
Version: 1.0
"""

from typing import Dict, Any
from core.base_commands import BaseCommands


class WakeLinkCommands(BaseCommands):
    """Unified command implementation for all WakeLink transports.
    
    Wraps a transport handler and delegates command execution.
    The handler is responsible for packet creation, encryption,
    transmission, and response decryption.
    
    Attributes:
        handler: Transport handler (TCPHandler or CloudClient).
    
    Example:
        >>> handler = TCPHandler(token="...", ip="192.168.1.50")
        >>> commands = WakeLinkCommands(handler)
        >>> result = commands.ping_device()
        >>> print(result['status'])
        success
    """
    
    def __init__(self, handler):
        """Initialize with a transport handler.
        
        Args:
            handler: Any object implementing send_command(cmd, data) method.
        """
        self.handler = handler

    def ping_device(self) -> Dict[str, Any]:
        """Send ping command to test device connectivity.
        
        Returns:
            Dict with status and optional latency info.
        """
        return self.handler.send_command("ping")

    def wake_device(self, mac: str) -> Dict[str, Any]:
        """Send Wake-on-LAN magic packet for specified MAC.
        
        Args:
            mac: Target MAC address (format: XX:XX:XX:XX:XX:XX).
            
        Returns:
            Dict confirming WOL packet transmission.
        """
        return self.handler.send_command("wake", {"mac": mac})

    def device_info(self) -> Dict[str, Any]:
        """Request device information.
        
        Returns:
            Dict containing version, IP, memory, uptime, etc.
        """
        return self.handler.send_command("info")

    def restart_device(self) -> Dict[str, Any]:
        """Request device restart.
        
        Returns:
            Dict confirming restart command received.
        """
        return self.handler.send_command("restart")

    def ota_start(self) -> Dict[str, Any]:
        """Enable OTA update mode (30 second window).
        
        Returns:
            Dict confirming OTA mode activated.
        """
        return self.handler.send_command("ota_start")

    def open_setup(self) -> Dict[str, Any]:
        """Enter device configuration mode.
        
        Returns:
            Dict with setup mode status.
        """
        return self.handler.send_command("open_setup")

    def enable_site(self) -> Dict[str, Any]:
        """Enable the device's built-in web server.
        
        Returns:
            Dict confirming web server enabled.
        """
        return self.handler.send_command("web_control", {"action": "enable"})

    def disable_site(self) -> Dict[str, Any]:
        """Disable the device's built-in web server.
        
        Returns:
            Dict confirming web server disabled.
        """
        return self.handler.send_command("web_control", {"action": "disable"})

    def site_status(self) -> Dict[str, Any]:
        """Get web server status.
        
        Returns:
            Dict with web server enabled/disabled state.
        """
        return self.handler.send_command("web_control", {"action": "status"})

    def crypto_info(self) -> Dict[str, Any]:
        """Get cryptographic status information.
        
        Returns:
            Dict with request counter, limit, and EEPROM status.
        """
        return self.handler.send_command("crypto_info")

    def update_token(self) -> Dict[str, Any]:
        """Request device token refresh.
        
        Generates a new device token. The old token becomes invalid.
        
        Returns:
            Dict with new_token field on success.
        """
        return self.handler.send_command("update_token")

    def enable_cloud(self) -> Dict[str, Any]:
        """Enable the device's cloud (WSS) connection.
        
        Returns:
            Dict confirming cloud mode enabled.
        """
        return self.handler.send_command("cloud_control", {"action": "enable"})

    def disable_cloud(self) -> Dict[str, Any]:
        """Disable the device's cloud (WSS) connection.
        
        Returns:
            Dict confirming cloud mode disabled.
        """
        return self.handler.send_command("cloud_control", {"action": "disable"})

    def cloud_status(self) -> Dict[str, Any]:
        """Get cloud connection status.
        
        Returns:
            Dict with cloud enabled/disabled state and connection info.
        """
        return self.handler.send_command("cloud_control", {"action": "status"})
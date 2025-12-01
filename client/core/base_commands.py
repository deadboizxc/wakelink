"""Base Command Interface for WakeLink Protocol.

This module defines the abstract base class for WakeLink commands.
All transport handlers (TCP, Cloud, WSS) implement this interface
to provide consistent command execution across different transports.

Protocol Commands:
    - ping: Test device connectivity
    - wake: Send Wake-on-LAN magic packet
    - info: Get device information
    - restart: Restart the device
    - ota_start: Enable OTA update mode
    - open_setup: Enter configuration mode
    - enable_site/disable_site/site_status: Web server control
    - crypto_info: Get encryption status

Author: deadboizxc
Version: 1.0
"""

from abc import ABC, abstractmethod


class BaseCommands(ABC):
    """Abstract base class defining the WakeLink command interface.
    
    All command implementations must inherit from this class and
    implement the abstract methods. Optional commands have default
    implementations that return "Not supported" errors.
    
    This interface ensures consistent command handling across:
    - TCPHandler: Local network communication
    - CloudClient: HTTP/WSS cloud relay (supports both protocols)
    """
    
    @abstractmethod
    def ping_device(self): 
        """Test connection with the device.
        
        Returns:
            Dict with status and latency information.
        """
        pass
    
    @abstractmethod
    def wake_device(self, mac): 
        """Send Wake-on-LAN magic packet.
        
        Args:
            mac: Target MAC address in format XX:XX:XX:XX:XX:XX.
            
        Returns:
            Dict confirming WOL packet was sent.
        """
        pass
    
    @abstractmethod
    def device_info(self): 
        """Retrieve device status and information.
        
        Returns:
            Dict containing firmware version, IP, memory, uptime, etc.
        """
        pass
    
    @abstractmethod
    def restart_device(self): 
        """Restart the WakeLink device.
        
        Returns:
            Dict confirming restart initiated.
        """
        pass
    
    @abstractmethod
    def ota_start(self): 
        """Enable OTA (Over-The-Air) update mode.
        
        Opens a 30-second window for Arduino IDE network upload.
        
        Returns:
            Dict confirming OTA mode enabled.
        """
        pass

    # =============================
    # Optional Commands (with default implementations)
    # =============================

    def open_setup(self): 
        """Enter device configuration mode.
        
        Returns:
            Dict with status or "Not supported" error.
        """
        return {"status": "error", "error": "Not supported"}
    
    def enable_site(self): 
        """Enable the device's built-in web server.
        
        Returns:
            Dict with status or "Not supported" error.
        """
        return {"status": "error", "error": "Not supported"}
    
    def disable_site(self): 
        """Disable the device's built-in web server.
        
        Returns:
            Dict with status or "Not supported" error.
        """
        return {"status": "error", "error": "Not supported"}
    
    def site_status(self): 
        """Get the web server status.
        
        Returns:
            Dict with web server state or "Not supported" error.
        """
        return {"status": "error", "error": "Not supported"}
    
    def crypto_info(self): 
        """Get cryptographic status and counter information.
        
        Returns request counter, limit, and EEPROM persistence status.
        
        Returns:
            Dict with crypto status or "Not supported" error.
        """
        return {"status": "error", "error": "Not supported"}
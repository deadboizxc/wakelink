"""WakeLink Client Core Module.

This package contains the core functionality for the WakeLink Python client.

Submodules:
    crypto: ChaCha20 encryption and HMAC-SHA256 signing.
    device_manager: Persistent device configuration storage.
    helpers: Utility functions (MAC address formatting, etc.).
    base_commands: Abstract command interface definition.
    
Subpackages:
    protocol: Packet creation and parsing (PacketManager, WakeLinkCommands).
    handlers: Transport implementations (TCP, Cloud, WSS).

Protocol Version: 1.0
Author: deadboizxc
"""
"""WakeLink Protocol v1.0 Module.

This package implements the WakeLink communication protocol v1.0.

Components:
    PacketManager: Creates and parses encrypted protocol packets.
    WakeLinkCommands: Command implementations using the protocol.

Protocol Specification:
    - Outer JSON: {device_id, payload, signature, version}
    - Payload: hex string = [uint16_be length] + [ciphertext] + [16B nonce]
    - Signature: HMAC-SHA256 of payload hex string only
    - Encryption: ChaCha20 with key derived from SHA256(device_token)

Author: deadboizxc
Version: 1.0
"""

from .packet import PacketManager
from .commands import WakeLinkCommands

__all__ = ["PacketManager", "WakeLinkCommands"]

"""
WakeLink Protocol v1.0 Packet Manager.

Handles creation and processing of signed, encrypted packets for
communication with WakeLink devices. Compatible with firmware packet.cpp.

Packet format:
- Outer JSON: {"device_id", "payload", "signature", "version"}
- Payload: hex string = [uint16_be length] + [ciphertext] + [16-byte nonce]
- Signature: HMAC-SHA256 of payload hex string only

The server acts as a transparent relay and never decrypts the payload.
"""

import json
import time
import uuid
from typing import Any, Dict, Optional

from ..crypto import Crypto


class PacketManager:
    """Manages packet creation and processing for WakeLink protocol v1.0.
    
    Attributes:
        crypto: Crypto instance for encryption/signing.
        device_id: Device identifier for packet headers.
    """
    
    PROTOCOL_VERSION = "1.0"
    
    def __init__(self, token: str, device_id: str):
        """Initialize packet manager.
        
        Args:
            token: Device token (min 32 chars) for key derivation.
            device_id: Device identifier for packet headers.
        """
        self.crypto = Crypto(token)
        self.device_id = device_id
    
    def create_command_packet(self, command: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Create a signed, encrypted command packet.
        
        Args:
            command: Command name (e.g., "ping", "wake", "info").
            data: Optional command parameters.
            
        Returns:
            JSON string of outer packet ready for transmission.
        """
        # Build inner packet
        inner = {
            "command": command,
            "data": data or {},
            "request_id": str(uuid.uuid4())[:8],
            "timestamp": int(time.time())
        }
        
        # Encrypt inner packet
        inner_json = json.dumps(inner, separators=(",", ":"))
        payload_hex = self.crypto.create_secure_response(inner_json)
        
        # Calculate HMAC on payload only
        signature = self.crypto.calculate_hmac(payload_hex)
        
        # Build outer packet
        outer = {
            "device_id": self.device_id,
            "payload": payload_hex,
            "signature": signature,
            "version": self.PROTOCOL_VERSION
        }
        
        return json.dumps(outer, separators=(",", ":"))
    
    def process_incoming_packet(self, packet_json: str) -> Dict[str, Any]:
        """Process an incoming signed, encrypted packet.
        
        Args:
            packet_json: JSON string of outer packet.
            
        Returns:
            Dict with status, decrypted data, and counter from ESP.
        """
        try:
            # Parse outer packet
            outer = json.loads(packet_json)
        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"JSON_PARSE_ERROR: {e}"}
        
        # Validate required fields
        required = ["device_id", "payload", "signature"]
        for field in required:
            if field not in outer:
                return {"status": "error", "error": f"MISSING_FIELD: {field}"}
        
        payload_hex = outer["payload"]
        signature = outer["signature"]
        
        # Verify HMAC signature (on payload only)
        if not self.crypto.verify_hmac(payload_hex, signature):
            return {"status": "error", "error": "INVALID_SIGNATURE"}
        
        # Decrypt payload
        decrypted = self.crypto.process_secure_packet(payload_hex)
        
        if decrypted.startswith("ERROR:"):
            return {"status": "error", "error": decrypted}
        
        # Parse inner packet
        try:
            inner = json.loads(decrypted)
        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"INNER_JSON_ERROR: {e}"}
        
        # Build successful response with counter from outer packet
        result = {"status": "success"}
        
        # Add counter from outer packet (synced from ESP)
        if "counter" in outer:
            result["counter"] = outer["counter"]
        
        result.update(inner)
        
        return result
    
    def create_response_packet(self, response_data: Dict[str, Any]) -> str:
        """Create a signed, encrypted response packet.
        
        Used by the device to send responses back to the client.
        
        Args:
            response_data: Response data to encrypt and sign.
            
        Returns:
            JSON string of outer packet.
        """
        # Add timestamp if not present
        if "timestamp" not in response_data:
            response_data["timestamp"] = int(time.time())
        
        # Encrypt response
        inner_json = json.dumps(response_data, separators=(",", ":"))
        payload_hex = self.crypto.create_secure_response(inner_json)
        
        # Calculate HMAC on payload only
        signature = self.crypto.calculate_hmac(payload_hex)
        
        # Build outer packet
        outer = {
            "device_id": self.device_id,
            "payload": payload_hex,
            "signature": signature,
            "version": self.PROTOCOL_VERSION
        }
        
        return json.dumps(outer, separators=(",", ":"))

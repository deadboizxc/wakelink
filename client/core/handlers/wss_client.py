"""WakeLink WSS Client Handler.

.. deprecated:: 1.0
    This module is deprecated. Use CloudClient with protocol='wss' instead.
    CloudClient provides unified HTTP and WSS support in a single class.

Provides WebSocket Secure transport for real-time device communication.
Uses protocol v1.0 packet format with ChaCha20 encryption and HMAC-SHA256.

Requires websocket-client package:
    pip install websocket-client

Falls back gracefully if websocket-client is not installed.

Migration:
    # Old (deprecated):
    from core.handlers.wss_client import WSSClient
    client = WSSClient(token, device_id, api_token, base_url)
    
    # New (recommended):
    from core.handlers.cloud_client import CloudClient
    client = CloudClient(token, device_id, api_token, base_url, protocol='wss')
"""

import json
import uuid
import warnings
from typing import Any, Dict, Optional

try:
    from websocket import create_connection, WebSocketException, WebSocketTimeoutException
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    create_connection = None
    WebSocketException = Exception
    WebSocketTimeoutException = Exception

from ..protocol.packet import PacketManager


class WSSClient:
    """WebSocket Secure client for WakeLink protocol v1.0.
    
    Uses identical packet format as TCP/HTTP:
    - Outer JSON: {device_id, payload, signature, version}
    - Payload: encrypted inner packet with command/data/request_id/timestamp
    
    Attributes:
        token: Device token for encryption.
        device_id: Device identifier.
        api_token: Optional API token for authentication.
        base_url: WSS server URL.
    """
    
    DEFAULT_TIMEOUT = 10
    DEVICE_RESPONSE_TIMEOUT = 10  # 10 seconds max for device response
    
    def __init__(
        self,
        token: str,
        device_id: str,
        api_token: Optional[str] = None,
        base_url: str = "wss://wakelink.deadboizxc.org"
    ):
        """Initialize WSS client.
        
        .. deprecated:: 1.0
            Use CloudClient with protocol='wss' instead.
        """
        warnings.warn(
            "WSSClient is deprecated. Use CloudClient(protocol='wss') instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        if not WEBSOCKET_AVAILABLE:
            raise ImportError(
                "websocket-client library required for WSS transport. "
                "Install with: pip install websocket-client"
            )
        
        self.token = token
        self.device_id = device_id
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        
        self.packet_manager = PacketManager(token, device_id)
        
        self._ws = None
        self._connected = False
        self._client_id = f"cli_{device_id}_{uuid.uuid4().hex[:8]}"
    
    def _get_wss_url(self) -> str:
        """Build WSS client endpoint URL (no token in URL)."""
        return f"{self.base_url}/ws/client/{self._client_id}"
    
    def connect(self) -> bool:
        """Establish WSS connection.
        
        Authentication is done via JSON message after connection:
        {"type": "auth", "token": "<api_token>"}
        """
        if self._connected and self._ws:
            return True
        
        try:
            url = self._get_wss_url()
            print(f"[WSS] Connecting to {url}")
            
            # Keep headers for backwards compatibility with older servers
            headers = []
            if self.api_token:
                headers.append(f"Authorization: Bearer {self.api_token}")
                headers.append(f"X-API-Token: {self.api_token}")
            headers.append(f"X-Device-ID: {self.device_id}")
            
            self._ws = create_connection(
                url,
                header=headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            # Send auth message with token in JSON body
            if self.api_token:
                auth_message = json.dumps({
                    "type": "auth",
                    "token": self.api_token
                })
                self._ws.send(auth_message)
                print("[WSS] Auth message sent")
            
            # Read server welcome
            try:
                self._ws.settimeout(3)
                welcome = self._ws.recv()
                data = json.loads(welcome)
                
                # Check for auth error
                if data.get("status") == "error":
                    error = data.get("error", "UNKNOWN")
                    message = data.get("message", "Authentication failed")
                    print(f"[WSS] Auth error: {error} - {message}")
                    self._ws.close()
                    self._ws = None
                    return False
                
                print(f"[WSS] Server: {data.get('message', 'connected')}")
            except Exception:
                pass
            finally:
                self._ws.settimeout(self.DEFAULT_TIMEOUT)
            
            self._connected = True
            print("[WSS] Connected successfully")
            return True
            
        except Exception as e:
            print(f"[WSS] Connection failed: {e}")
            self._connected = False
            self._ws = None
            return False
    
    def disconnect(self):
        """Close WSS connection."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected and self._ws is not None
    
    def send_command(self, command: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send command via WSS and wait for response."""
        if not self.is_connected():
            if not self.connect():
                return {"status": "error", "error": "WSS_CONNECTION_FAILED"}
        
        try:
            packet = self.packet_manager.create_command_packet(command, data or {})
            self._ws.send(packet)
            print(f"[WSS] Sent: {command}")
            
            # Wait for server ACK
            self._ws.settimeout(self.DEFAULT_TIMEOUT)
            ack_raw = self._ws.recv()
            ack = json.loads(ack_raw)
            
            # Check for error
            if ack.get("status") == "error":
                return {"status": "error", "error": ack.get("error", "UNKNOWN")}
            
            # Device offline
            if ack.get("queued"):
                return {
                    "status": "queued",
                    "message": "Command queued, device offline",
                    "device_id": ack.get("device_id")
                }
            
            # Device online - wait for response
            if ack.get("delivered"):
                print(f"[WSS] Waiting for device response (max {self.DEVICE_RESPONSE_TIMEOUT}s)...")
                try:
                    self._ws.settimeout(self.DEVICE_RESPONSE_TIMEOUT)
                    response_raw = self._ws.recv()
                    
                    resp = json.loads(response_raw)
                    if "payload" in resp:
                        return self.packet_manager.process_incoming_packet(response_raw)
                    return resp
                    
                except (WebSocketTimeoutException, TimeoutError, OSError) as e:
                    print(f"[WSS] Timeout waiting for device: {e}")
                    return {
                        "status": "timeout",
                        "message": "Device did not respond within timeout",
                        "delivered": True
                    }
                finally:
                    self._ws.settimeout(self.DEFAULT_TIMEOUT)
            
            return ack
            
        except WebSocketException as e:
            print(f"[WSS] WebSocket error: {e}")
            self.disconnect()
            return {"status": "error", "error": f"WSS_ERROR: {e}"}
        except Exception as e:
            print(f"[WSS] Error: {e}")
            return {"status": "error", "error": str(e)}
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


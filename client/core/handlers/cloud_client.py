"""
WakeLink Cloud Client Handler.

Unified cloud transport supporting both HTTP (push/pull) and WSS (WebSocket).
Protocol is selected based on device config 'protocol' field: 'http' or 'wss'.

Usage:
    # HTTP mode (push/pull relay)
    wl add mydevice token TOKEN url https://server.com protocol http
    
    # WSS mode (real-time WebSocket)  
    wl add mydevice token TOKEN url wss://server.com protocol wss

Transport Selection:
    - protocol='http': Uses POST /api/push + GET /api/pull polling
    - protocol='wss': Uses persistent WebSocket connection to /ws/client/{id}

Author: deadboizxc
Version: 1.0
"""

import json
import time
import uuid
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from ..protocol.packet import PacketManager

# Check for websocket-client availability
try:
    from websocket import create_connection, WebSocketException, WebSocketTimeoutException
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocketException = Exception
    WebSocketTimeoutException = Exception


class CloudClient:
    """Unified cloud handler supporting HTTP and WSS transports.
    
    Attributes:
        token: Device token for encryption.
        device_id: Device identifier.
        api_token: API token for cloud authentication.
        base_url: Cloud server base URL.
        protocol: Transport protocol ('http' or 'wss').
    """
    
    DEFAULT_BASE_URL = "https://wakelink.deadboizxc.org"
    HTTP_TIMEOUT = 35  # Increased for long polling (30s wait + 5s buffer)
    WSS_TIMEOUT = 10
    DEVICE_RESPONSE_TIMEOUT = 30
    LONG_POLL_WAIT = 15  # Server waits up to 15 seconds for messages
    
    def __init__(
        self,
        token: str,
        device_id: str,
        api_token: str = None,
        base_url: str = None,
        protocol: str = "wss"
    ):
        """Initialize cloud client.
        
        Args:
            token: Device secret token for encryption.
            device_id: Unique device identifier.
            api_token: API bearer token for authentication.
            base_url: Server URL (https:// or wss://).
            protocol: Transport protocol - 'http' or 'wss'.
        """
        self.token = token
        self.device_id = device_id
        self.api_token = api_token or ""
        self.protocol = protocol.lower() if protocol else "wss"
        
        # Normalize base URL
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            self.base_url = self.DEFAULT_BASE_URL
        
        # Derive HTTP URL from WSS URL if needed
        if self.base_url.startswith("wss://"):
            self.http_url = self.base_url.replace("wss://", "https://")
        elif self.base_url.startswith("ws://"):
            self.http_url = self.base_url.replace("ws://", "http://")
        else:
            self.http_url = self.base_url
        
        # Derive WSS URL from HTTP URL if needed
        if self.base_url.startswith("https://"):
            self.wss_url = self.base_url.replace("https://", "wss://")
        elif self.base_url.startswith("http://"):
            self.wss_url = self.base_url.replace("http://", "ws://")
        else:
            self.wss_url = self.base_url
        
        # Initialize packet manager for encryption
        self.packet_manager = PacketManager(token, device_id)
        
        # Stable client ID for WSS sessions
        self._client_id = f"cli_{device_id}_{uuid.uuid4().hex[:8]}"
        
        # HTTP session with retry logic
        self._session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self._session.mount("https://", HTTPAdapter(max_retries=retries))
        self._session.mount("http://", HTTPAdapter(max_retries=retries))
        
        # WSS connection state
        self._ws = None
    
    def send_command(self, command: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send command using configured protocol.
        
        Args:
            command: Command name (e.g., 'ping', 'wake').
            data: Optional command parameters.
            
        Returns:
            Response dictionary with status and result.
        """
        if self.protocol == "http":
            return self._send_http(command, data)
        else:
            return self._send_wss(command, data)
    
    # ==================== HTTP Transport ====================
    
    def _send_http(self, command: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send command via HTTP push/pull relay.
        
        1. POST encrypted packet to /api/push
        2. Poll GET /api/pull for device response
        
        Args:
            command: Command name.
            data: Command parameters.
            
        Returns:
            Device response or error dict.
        """
        print(f"[HTTP] Sending to {self.http_url}")
        
        # Build encrypted packet (returns JSON string)
        packet_json = self.packet_manager.create_command_packet(command, data or {})
        packet = json.loads(packet_json)
        request_id = None
        
        # Extract request_id from decrypted inner if possible
        try:
            inner = self.packet_manager.process_incoming_packet(packet_json)
            request_id = inner.get("request_id")
        except:
            pass
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Push command to server
        try:
            push_data = {
                "device_id": self.device_id,
                "payload": packet["payload"],
                "signature": packet["signature"],
                "version": packet.get("version", "1.0"),
                "direction": "to_device",
                "client_id": self._client_id
            }
            
            resp = self._session.post(
                f"{self.http_url}/api/push",
                headers=headers,
                json=push_data,
                timeout=self.HTTP_TIMEOUT
            )
            resp.raise_for_status()
            push_result = resp.json()
            print(f"[HTTP] Push: {push_result.get('status', 'unknown')}")
            
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"HTTP push failed: {e}"}
        
        # Poll for response
        print(f"[HTTP] Waiting for device response...")
        return self._poll_response(headers, request_id)
    
    def _poll_response(self, headers: Dict, request_id: str) -> Dict[str, Any]:
        """Poll server for device response using long polling.
        
        Long polling: Server holds connection for up to LONG_POLL_WAIT seconds
        until messages arrive, making HTTP nearly as fast as WSS.
        
        Args:
            headers: HTTP headers with auth.
            request_id: Expected request ID to match.
            
        Returns:
            Device response or timeout error.
        """
        start_time = time.time()
        max_attempts = 2  # With 15s long poll, 2 attempts = 30s total
        
        for attempt in range(max_attempts):
            try:
                # Long polling request - server waits for messages
                pull_data = {
                    "device_id": self.device_id,
                    "direction": "to_client",  # Responses from device TO client
                    "wait": self.LONG_POLL_WAIT  # Server waits up to N seconds
                }
                resp = self._session.post(
                    f"{self.http_url}/api/pull",
                    headers=headers,
                    json=pull_data,
                    timeout=self.HTTP_TIMEOUT
                )
                resp.raise_for_status()
                result = resp.json()
                
                # Check if we got messages
                messages = result.get("messages", [])
                if messages:
                    for msg in messages:
                        payload = msg.get("payload")
                        signature = msg.get("signature")
                        
                        if payload and signature:
                            # Build full packet for processing
                            try:
                                full_packet = {
                                    "device_id": self.device_id,
                                    "payload": payload,
                                    "signature": signature,
                                    "version": msg.get("version", "1.0")
                                }
                                decrypted = self.packet_manager.process_incoming_packet(json.dumps(full_packet))
                                if decrypted and decrypted.get("status") == "success":
                                    # Check request_id matches
                                    if decrypted.get("request_id") == request_id or not request_id:
                                        return decrypted
                            except Exception as e:
                                print(f"[HTTP] Decrypt error: {e}")
                
            except requests.exceptions.RequestException as e:
                print(f"[HTTP] Poll error: {e}")
                # Don't retry on network errors
                break
        
        return {"status": "timeout", "message": "No response from device"}
    
    # ==================== WSS Transport ====================
    
    def _send_wss(self, command: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send command via WebSocket.
        
        Args:
            command: Command name.
            data: Command parameters.
            
        Returns:
            Device response or error dict.
        """
        if not WEBSOCKET_AVAILABLE:
            print("[WSS] websocket-client not installed, falling back to HTTP")
            return self._send_http(command, data)
        
        # Connect if needed
        if not self._connect_wss():
            print("[WSS] Connection failed, falling back to HTTP")
            return self._send_http(command, data)
        
        # Build encrypted packet (returns JSON string)
        packet_json = self.packet_manager.create_command_packet(command, data or {})
        packet = json.loads(packet_json)
        
        # Extract request_id from inner packet for response matching
        try:
            inner = self.packet_manager.process_incoming_packet(packet_json)
            request_id = inner.get("request_id")
        except Exception:
            request_id = None
        
        # Send packet
        try:
            message = {
                "device_id": self.device_id,
                "payload": packet["payload"],
                "signature": packet["signature"],
                "version": packet.get("version", "1.0")
            }
            
            self._ws.send(json.dumps(message))
            print(f"[WSS] Command sent: {command}")
            
        except Exception as e:
            self._close_wss()
            return {"status": "error", "message": f"WSS send failed: {e}"}
        
        # Wait for response
        return self._wait_wss_response(request_id)
    
    def _connect_wss(self) -> bool:
        """Establish WebSocket connection if not connected.
        
        Authentication is done via JSON message after connection:
        {"type": "auth", "token": "<api_token>"}
        
        Returns:
            True if connected and authenticated, False on failure.
        """
        if self._ws:
            return True
        
        # Build WSS URL for client endpoint (no token in URL)
        ws_url = f"{self.wss_url}/ws/client/{self._client_id}"
        
        print(f"[WSS] Connecting to {ws_url}")
        
        try:
            # Keep headers for backwards compatibility with older servers
            headers = []
            if self.api_token:
                headers.append(f"Authorization: Bearer {self.api_token}")
                headers.append(f"X-API-Token: {self.api_token}")
                headers.append(f"X-Device-ID: {self.device_id}")
            
            self._ws = create_connection(
                ws_url,
                timeout=self.WSS_TIMEOUT,
                header=headers if headers else None
            )
            
            # Send auth message with token in JSON body
            if self.api_token:
                auth_message = json.dumps({
                    "type": "auth",
                    "token": self.api_token
                })
                self._ws.send(auth_message)
                print("[WSS] Auth message sent")
            
            # Read and handle welcome message
            try:
                self._ws.settimeout(2.0)
                welcome = self._ws.recv()
                welcome_data = json.loads(welcome)
                
                # Check for auth error
                if welcome_data.get("status") == "error":
                    error = welcome_data.get("error", "UNKNOWN")
                    message = welcome_data.get("message", "Authentication failed")
                    print(f"[WSS] Auth error: {error} - {message}")
                    self._ws.close()
                    self._ws = None
                    return False
                
                # Server sends status="connected" for successful connection
                if welcome_data.get("status") == "connected":
                    print(f"[WSS] Server: {welcome_data.get('message', 'Connected')}")
                elif welcome_data.get("type") == "welcome":
                    # Legacy compatibility
                    print(f"[WSS] Server: {welcome_data.get('message', 'Connected')}")
                else:
                    # Not a welcome message, might be actual data - skip for now
                    pass
                    
            except Exception:
                # No welcome message or timeout - that's fine
                pass
            
            self._ws.settimeout(self.DEVICE_RESPONSE_TIMEOUT)
            print("[WSS] Connected successfully")
            return True
            
        except Exception as e:
            print(f"[WSS] Connection failed: {e}")
            self._ws = None
            return False
    
    def _wait_wss_response(self, request_id: str) -> Dict[str, Any]:
        """Wait for device response on WebSocket.
        
        Args:
            request_id: Expected request ID.
            
        Returns:
            Device response or error dict.
        """
        start_time = time.time()
        
        while time.time() - start_time < self.DEVICE_RESPONSE_TIMEOUT:
            try:
                raw = self._ws.recv()
                msg = json.loads(raw)
                
                # Skip server status messages (welcome, connection status, etc.)
                if msg.get("type") in ("welcome", "status", "ping", "pong", "ack"):
                    continue
                
                # Skip server connection confirmation
                if msg.get("status") == "connected":
                    continue
                
                # Handle server ACK for command delivery
                if msg.get("status") == "success" and msg.get("delivered") is not None:
                    delivered = msg.get("delivered")
                    queued = msg.get("queued", not delivered)
                    
                    if queued:
                        return {
                            "status": "queued",
                            "message": msg.get("message", "Device offline, command queued"),
                            "device_id": msg.get("device_id")
                        }
                    
                    # Command was delivered, continue waiting for device response
                    print(f"[WSS] Command delivered, waiting for response...")
                    continue
                
                # Skip queued/delivered status messages (uppercase variants)
                if msg.get("status") in ("QUEUED", "DELIVERED"):
                    status_msg = msg.get("message", msg.get("status"))
                    print(f"[WSS] Status: {status_msg}")
                    continue
                
                # Check for payload (device response)
                payload = msg.get("payload")
                signature = msg.get("signature")
                
                if payload and signature:
                    try:
                        full_packet = {
                            "device_id": self.device_id,
                            "payload": payload,
                            "signature": signature,
                            "version": msg.get("version", "1.0")
                        }
                        decrypted = self.packet_manager.process_incoming_packet(json.dumps(full_packet))
                        if decrypted and decrypted.get("status") == "success":
                            # Match request_id if provided
                            if not request_id or decrypted.get("request_id") == request_id:
                                return decrypted
                    except Exception as e:
                        print(f"[WSS] Decrypt error: {e}")
                
            except WebSocketTimeoutException:
                break
            except Exception as e:
                print(f"[WSS] Receive error: {e}")
                self._close_wss()
                break
        
        return {"status": "timeout", "message": "No response from device"}
    
    def _close_wss(self):
        """Close WebSocket connection."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
    
    def close(self):
        """Clean up resources."""
        self._close_wss()
        self._session.close()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()

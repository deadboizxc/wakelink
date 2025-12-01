"""
WakeLink TCP Handler.

Provides local TCP transport for direct device communication on port 99.
Uses protocol v1.0 packet format with ChaCha20 encryption and HMAC-SHA256.

This is the simplest and fastest transport for local network communication.
"""

import socket
import time
from typing import Any, Dict, Optional

from ..protocol.packet import PacketManager


class TCPHandler:
    """TCP handler for local device communication.
    
    Connects directly to the device over TCP port 99 (default).
    All packets are encrypted and signed per protocol v1.0.
    
    Attributes:
        ip: Device IP address.
        port: TCP port (default 99).
        timeout: Socket timeout in seconds.
        device_id: Device identifier for packets.
    """
    
    DEFAULT_PORT = 99
    DEFAULT_TIMEOUT = 10.0
    
    def __init__(
        self,
        token: str,
        ip: str,
        device_id: str = "python_client",
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """Initialize TCP handler.
        
        Args:
            token: Device token for packet encryption (min 32 chars).
            ip: Device IP address.
            device_id: Device identifier for packet headers.
            port: TCP port number (default 99).
            timeout: Socket timeout in seconds.
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.device_id = device_id
        
        # Initialize packet manager
        self.packet_manager = PacketManager(token, device_id)
    
    def send_command(self, command: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send command to device via TCP.
        
        Opens a TCP connection, sends the encrypted packet, and waits
        for the response. Connection is closed after each command.
        
        Args:
            command: Command name (e.g., "ping", "wake", "info").
            data: Optional command parameters.
            
        Returns:
            Dict with command response or error info.
        """
        try:
            with socket.create_connection((self.ip, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                
                # Create encrypted packet
                packet = self.packet_manager.create_command_packet(command, data or {})
                
                # Send packet with newline terminator
                sock.sendall((packet + "\n").encode("utf-8"))
                print(f"[TCP] Sent: {command} ({len(packet)} bytes)")
                
                # Receive response
                response = self._receive_response(sock)
                
                if not response:
                    return {"status": "error", "error": "NO_RESPONSE"}
                
                # Process response packet
                return self.packet_manager.process_incoming_packet(response)
                
        except socket.timeout:
            return {"status": "error", "error": "TIMEOUT"}
        except ConnectionRefusedError:
            return {"status": "error", "error": "CONNECTION_REFUSED"}
        except OSError as e:
            return {"status": "error", "error": f"CONNECTION_ERROR: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"ERROR: {e}"}
    
    def _receive_response(self, sock: socket.socket) -> Optional[str]:
        """Receive response from socket until newline or timeout.
        
        Args:
            sock: Connected socket.
            
        Returns:
            Response string or None if no data received.
        """
        buffer = b""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                    
                buffer += chunk
                
                # Check for newline terminator
                if b"\n" in buffer:
                    break
                    
            except socket.timeout:
                break
            except BlockingIOError:
                time.sleep(0.01)
                continue
        
        if not buffer:
            return None
        
        return buffer.decode("utf-8", errors="ignore").strip()

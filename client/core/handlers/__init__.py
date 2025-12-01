"""WakeLink Transport Handlers Module.

This package provides transport handlers for communicating with WakeLink devices.

Available Handlers:
    TCPHandler: Direct local TCP connection (port 99).
    CloudClient: Unified cloud transport supporting HTTP and WSS.

Transport Selection:
    - Local devices: Use TCPHandler for lowest latency
    - Cloud devices: Use CloudClient with protocol='http' or 'wss'

Protocol Options:
    - protocol='http': HTTP push/pull relay (always works)
    - protocol='wss': WebSocket real-time (faster, requires websocket-client)

WSS Availability:
    WebSocket support requires the 'websocket-client' package:
        pip install websocket-client
    
    WEBSOCKET_AVAILABLE flag indicates if WSS is usable.

Author: deadboizxc
Version: 1.0
"""

from .tcp_handler import TCPHandler
from .cloud_client import CloudClient, WEBSOCKET_AVAILABLE

__all__ = ['TCPHandler', 'CloudClient', 'WEBSOCKET_AVAILABLE']

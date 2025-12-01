#!/usr/bin/env python3
"""
WakeLink Client v1.0 - Command Line Interface.

This module provides the main entry point for the WakeLink CLI application.
It handles command parsing, device management, and communication with
WakeLink devices via TCP (local) or Cloud (remote) transports.

Protocol:
    Uses WakeLink Protocol v1.0 with ChaCha20 encryption and HMAC-SHA256
    signatures. All communication is encrypted end-to-end.

Transports:
    - TCP: Direct local network communication on port 99
    - Cloud: HTTP/WSS relay through wakelink.deadboizxc.org

Usage:
    wl DEVICE COMMAND          Execute command on device
    wl add NAME ip IP token T  Add local TCP device
    wl register NAME ...       Register cloud device
    wl list                    Show configured devices
    wl help                    Show full help

Author: deadboizxc
Version: 1.0
"""

import argparse
import sys
import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

from core.protocol.commands import WakeLinkCommands
from core.handlers.tcp_handler import TCPHandler
from core.handlers.cloud_client import CloudClient, WEBSOCKET_AVAILABLE
from core.device_manager import DeviceManager, DEFAULT_HTTP_URL, DEFAULT_WSS_URL, DEFAULT_PROTOCOL, DEFAULT_PORT
from core.helpers import format_mac_address


# =============================
# Output Printer
# =============================
class OutputPrinter:
    """Utility class for formatted console output with ANSI colors.
    
    Provides consistent styling for success/error/info messages,
    device listings, and command response formatting.
    
    Attributes:
        COLORS: Dict mapping color names to ANSI escape codes.
    
    Note:
        Colors work in most modern terminals. Windows CMD may require
        enabling ANSI support via registry or using Windows Terminal.
    """

    # ANSI escape codes for terminal colors
    COLORS = {
        'green': '\033[92m',    # Success messages
        'yellow': '\033[93m',   # Warnings
        'red': '\033[91m',      # Errors
        'blue': '\033[94m',     # Info messages
        'magenta': '\033[95m',  # Commands
        'cyan': '\033[96m',     # Headers and labels
        'bold': '\033[1m',      # Bold text
        'end': '\033[0m'        # Reset formatting
    }
    
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Wrap text with ANSI color codes.
        
        Args:
            text: Text to colorize.
            color: Color name from COLORS dict.
            
        Returns:
            Text wrapped with color codes, or plain text if color not found.
        """
        return f"{cls.COLORS.get(color, '')}{text}{cls.COLORS['end']}"
    
    @classmethod
    def print_header(cls, text: str):
        """Print a boxed header with cyan color.
        
        Creates a visually distinct header for major sections.
        
        Args:
            text: Header text to display.
        """
        print(f"\n{cls.COLORS['bold']}{cls.COLORS['cyan']}╔{'═' * (len(text) + 2)}╗{cls.COLORS['end']}")
        print(f"{cls.COLORS['bold']}{cls.COLORS['cyan']}║ {text} ║{cls.COLORS['end']}")
        print(f"{cls.COLORS['bold']}{cls.COLORS['cyan']}╚{'═' * (len(text) + 2)}╝{cls.COLORS['end']}")
    
    @classmethod
    def print_success(cls, text: str):
        """Print a green success message with checkmark."""
        print(f"{cls.COLORS['green']}✅ {text}{cls.COLORS['end']}")
    
    @classmethod
    def print_error(cls, text: str):
        """Print a red error message with X mark."""
        print(f"{cls.COLORS['red']}❌ {text}{cls.COLORS['end']}")
    
    @classmethod
    def print_warning(cls, text: str):
        """Print a yellow warning message."""
        print(f"{cls.COLORS['yellow']}⚠️ {text}{cls.COLORS['end']}")
    
    @classmethod
    def print_info(cls, text: str):
        """Print a blue informational message."""
        print(f"{cls.COLORS['blue']}ℹ️ {text}{cls.COLORS['end']}")
    
    @classmethod
    def print_command(cls, command: str, mode: str):
        """Print command execution header with mode indicator.
        
        Args:
            command: Command name being executed.
            mode: Transport mode (CLOUD or LOCAL).
        """
        mode_icon = "☁️" if mode == "CLOUD" else "🔒"
        print(f"\n{cls.COLORS['bold']}{cls.COLORS['magenta']}🚀 Executing: {command.upper()}{cls.COLORS['end']}")
        print(f"{cls.COLORS['cyan']}   Mode: {mode_icon} {mode}{cls.COLORS['end']}")
        print(f"{cls.COLORS['cyan']}{'─' * 50}{cls.COLORS['end']}")
    
    @classmethod
    def format_response(cls, response: Dict[str, Any]) -> str:
        """Format a device response dictionary for display.
        
        Converts response dict to human-readable multi-line string
        with color-coded status and formatted key-value pairs.
        
        Args:
            response: Response dictionary from device command.
            
        Returns:
            Formatted string ready for printing.
        """
        if not response:
            return cls.colorize("Empty response", "red")
        
        # Determine status color based on response status
        status = response.get('status', 'unknown')
        status_color = 'green' if status == 'success' else 'red' if status == 'error' else 'yellow'
        output = [f"{cls.COLORS['bold']}Status: {cls.colorize(status.upper(), status_color)}{cls.COLORS['end']}"]
        
        for key, value in response.items():
            if key != 'status':
                if isinstance(value, dict):
                    output.append(f"{cls.COLORS['bold']}{key}:{cls.COLORS['end']}")
                    for sk, sv in value.items():
                        output.append(f"  {cls.colorize(sk, 'cyan')}: {sv}")
                else:
                    output.append(f"{cls.COLORS['bold']}{key}:{cls.COLORS['end']} {value}")
        
        return '\n'.join(output)
    
    @classmethod
    def print_device_added(cls, name: str, ip: str = None, port: int = 99, token: str = None, 
                          device_id: str = None, cloud: bool = False):
        """Display a confirmation message when a device is added."""
        if cloud:
            print(f"✅ Device '{name}' added (Cloud)")
            print(f"  ☁️  Cloud: Enabled")
        else:
            print(f"✅ Device '{name}' added (Local TCP)")
            print(f"  🌐 IP: {ip}:{port}")
        
        if token:
            print(f"  🔐 Token: {token[:8]}...{token[-4:]}")
        if device_id and device_id != name:
            print(f"  🆔 Device ID: {device_id}")
    
    @classmethod
    def print_device_removed(cls, name: str):
        print(f"✅ Device '{name}' removed")
    
    @classmethod
    def print_device_list(cls, devices: Dict[str, Dict[str, Any]]):
        """Show the list of configured devices."""
        if not devices:
            print("📭 No devices configured")
            return
        
        cls.print_header("MANAGED WAKELINK DEVICES")
        
        for name, info in devices.items():
            # Backward compatibility: fallback to old 'url' field
            legacy_url = info.get("url", "")
            http_url = info.get("http_url", "")
            wss_url = info.get("wss_url", "")
            
            if legacy_url and not http_url and not wss_url:
                if legacy_url.startswith(("wss://", "ws://")):
                    wss_url = legacy_url
                else:
                    http_url = legacy_url
            
            protocol = info.get("protocol", "").lower()
            
            # Determine mode from protocol field or URLs/cloud flag
            if http_url or wss_url or info.get("cloud"):
                if protocol == "wss":
                    mode = "WSS"
                    mode_color = 'magenta'
                elif protocol == "http":
                    mode = "HTTP"
                    mode_color = 'cyan'
                else:
                    # Default to HTTP if both URLs present
                    mode = "CLOUD"
                    mode_color = 'cyan'
            else:
                mode = "LOCAL"
                mode_color = 'blue'
            
            print(f"\n{cls.COLORS['bold']}{cls.colorize(name, 'green')}{cls.COLORS['end']}")
            print(f"  {cls.colorize('Mode:', 'cyan')}     {cls.colorize(mode, mode_color)}")
            
            if mode in ("HTTP", "WSS", "CLOUD"):
                device_id = info.get("device_id", name)
                token_preview = info.get("token", "N/A")[:16] + "..." if info.get("token") else "N/A"
                
                if http_url:
                    print(f"  {cls.colorize('HTTP URL:', 'cyan')} {http_url}")
                if wss_url:
                    print(f"  {cls.colorize('WSS URL:', 'cyan')}  {wss_url}")
                if protocol:
                    print(f"  {cls.colorize('Protocol:', 'cyan')} {protocol.upper()}")
                print(f"  {cls.colorize('Device ID:', 'cyan')} {device_id}")
                print(f"  {cls.colorize('Token:', 'cyan')}    {token_preview}")
                
                # Show the local IP address if available for reference
                if info.get("ip"):
                    print(f"  {cls.colorize('Local IP:', 'cyan')} {info['ip']}:{info.get('port', 99)}")
            else:
                ip = info.get("ip", "—")
                port = info.get("port", 99)
                token_preview = info.get("token", "N/A")[:16] + "..." if info.get("token") else "N/A"
                device_id = info.get("device_id", name)
                
                print(f"  {cls.colorize('Address:', 'cyan')} {ip}:{port}")
                print(f"  {cls.colorize('Token:', 'cyan')}   {token_preview}")
                if device_id != name:
                    print(f"  {cls.colorize('ID:', 'cyan')}      {device_id}")
            
            added_time = info.get("added", 0)
            if added_time:
                added_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(added_time))
                print(f"  {cls.colorize('Added:', 'cyan')}   {added_str}")


# =============================
# Smart Parser
# =============================
class SmartParser:
    """Intelligent argument parser for WakeLink CLI.
    
    Provides flexible command parsing supporting multiple input styles:
    - Positional: wl DEVICE COMMAND
    - Flag-based: wl --device DEVICE --ping
    - Mixed: wl mydevice --wake 00:11:22:33:44:55
    
    Features:
    - Command aliases (p=ping, w=wake, etc.)
    - Automatic device resolution from saved configs
    - IP/port/token detection from positional args
    - Backward compatibility with legacy flag syntax
    
    Attributes:
        COMMAND_MAP: Dict mapping aliases to canonical command names.
        parser: argparse.ArgumentParser for flag-style arguments.
        dev_mgr: DeviceManager for device lookup.
        printer: OutputPrinter for messages.
    """
    
    # Command aliases mapping to canonical names
    # Supports shortcuts, synonyms, and legacy names
    COMMAND_MAP = {
        # Device commands (no -- prefix)
        # Format: 'alias': 'canonical_name'
        'ping': 'ping', 'p': 'ping', 'test': 'ping',  # Connection test
        'info': 'info', 'i': 'info', 'information': 'info', 'status': 'info',  # Device info
        'wake': 'wake', 'w': 'wake', 'wol': 'wake', 'wakeonlan': 'wake',  # Wake-on-LAN
        'restart': 'restart', 'r': 'restart', 'reboot': 'restart', 'reset': 'restart',  # Restart
        'ota': 'ota_start', 'o': 'ota_start', 'update': 'ota_start', 'upgrade': 'ota_start',  # OTA update
        'setup': 'open_setup', 's': 'open_setup', 'config-mode': 'open_setup',  # Config mode
        'update-token': 'update_token', 'ut': 'update_token',  # Token refresh
        'token-update': 'update_token', 'refresh-token': 'update_token',
        'site-on': 'enable_site', 'enable-site': 'enable_site', 'web-on': 'enable_site',  # Web enable
        'site-off': 'disable_site', 'disable-site': 'disable_site', 'web-off': 'disable_site',  # Web disable
        'site': 'site_status', 'site-status': 'site_status', 'web-status': 'site_status',  # Web status
        'cloud-on': 'enable_cloud', 'enable-cloud': 'enable_cloud',  # Cloud enable
        'cloud-off': 'disable_cloud', 'disable-cloud': 'disable_cloud',  # Cloud disable
        'cloud-status': 'cloud_status',  # Cloud status
        'crypto': 'crypto_info', 'crypto-info': 'crypto_info', 'security': 'crypto_info',  # Crypto info
        
        # Device management helpers (no -- prefix)
        'list': 'list_devices', 'ls': 'list_devices', 'l': 'list_devices',  # List local devices
        'cloud-list': 'cloud_list_devices', 'cloud-ls': 'cloud_list_devices',  # List cloud devices
        'add': 'add_device', 'register': 'register_device', 'reg': 'register_device',  # Add/register
        'remove': 'remove_device', 'rm': 'remove_device', 'delete': 'remove_device',  # Remove device
        'update': 'update_device', 'set': 'update_device', 'edit': 'update_device',  # Update device fields
        
        # Help shortcuts
        'help': 'help', 'h': 'help', '?': 'help',  # Show help
    }
    
    # URL schemes for transport detection
    URL_SCHEMES = ('wss://', 'ws://', 'https://', 'http://')
    
    def __init__(self):
        """Initialize the smart parser with argument parser and device manager."""
        self.parser = self._build_parser()
        self.dev_mgr = DeviceManager()
        self.printer = OutputPrinter()
    
    def _build_parser(self):
        """Build the argparse parser with all supported options.
        
        Creates parser supporting both modern positional syntax and
        legacy flag-based syntax for backward compatibility.
        
        Returns:
            Configured ArgumentParser instance.
        """
        p = argparse.ArgumentParser(add_help=False, allow_abbrev=False, usage="%(prog)s [OPTIONS] [COMMAND]")
        
        # Core options (with -- prefix)
        # These define the target device and authentication
        p.add_argument("--device", "-d", help="Device name")
        p.add_argument("--ip", help="IP address")
        p.add_argument("--port", type=int, default=None, help="Port (default: 99)")
        p.add_argument("--token", "-t", help="Device token")
        p.add_argument("--api-token", "-a", help="API token")
        p.add_argument("--device-id", help="Device ID")
        p.add_argument("--cloud", "-c", action="store_true", help="Cloud mode")

        # Legacy flag aliases for command compatibility
        # These mirror positional commands for users preferring flag syntax
        p.add_argument("--ping", action="store_true")
        p.add_argument("--info", action="store_true")
        p.add_argument("--wake", metavar="MAC")
        p.add_argument("--restart", action="store_true")
        p.add_argument("--ota-start", action="store_true")
        p.add_argument("--open-setup", action="store_true")
        p.add_argument("--enable-site", action="store_true")
        p.add_argument("--disable-site", action="store_true")
        p.add_argument("--site-status", action="store_true")
        p.add_argument("--crypto-info", action="store_true")
        p.add_argument("--update-token", action="store_true")
        p.add_argument("--list-devices", action="store_true")
        p.add_argument("--cloud-list-devices", action="store_true")
        p.add_argument("--add-device", metavar="NAME")
        p.add_argument("--register-device", metavar="NAME")
        p.add_argument("--remove-device", metavar="NAME")
        p.add_argument("--delete-device", metavar="NAME")
        p.add_argument("--help", "-h", action="store_true", help="Show help")
        
        return p
    
    def parse(self, args: List[str]):
        if not args:
            return argparse.Namespace(help=True)
        
        if any(arg in ['help', '--help', '-h'] for arg in args):
            return argparse.Namespace(help=True)
        
        parsed = argparse.Namespace()
        remaining = []
        i = 0
        
        # Parser states to track positional expectations
        expect_device_name = False
        expect_wake_mac = False
        expect_add_name = False
        expect_remove_name = False
        expect_register_name = False
        expect_update_name = False
        expect_port_value = False
        expect_token_value = False
        expect_ip_value = False
        expect_device_id_value = False
        expect_api_token_value = False
        expect_http_url_value = False
        expect_wss_url_value = False
        expect_protocol_value = False
        expect_mode_value = False
        
        while i < len(args):
            arg = args[i]
            
            # If the argument starts with --, add it directly to the arg list
            if arg.startswith('--'):
                remaining.append(arg)
                i += 1
                continue
                
            lower_arg = arg.lower()
            
            # Handle expected values FIRST (these consume the next argument)
            if expect_port_value:
                parsed.port = int(arg)
                expect_port_value = False
                i += 1
                continue
            
            if expect_token_value:
                parsed.token = arg
                expect_token_value = False
                i += 1
                continue
            
            if expect_ip_value:
                parsed.ip = arg
                expect_ip_value = False
                i += 1
                continue
            
            if expect_device_id_value:
                parsed.device_id = arg
                expect_device_id_value = False
                i += 1
                continue
            
            if expect_api_token_value:
                parsed.api_token = arg
                expect_api_token_value = False
                i += 1
                continue
            
            if expect_http_url_value:
                parsed.http_url = arg
                expect_http_url_value = False
                i += 1
                continue
            
            if expect_wss_url_value:
                parsed.wss_url = arg
                expect_wss_url_value = False
                i += 1
                continue
            
            if expect_protocol_value:
                parsed.protocol = arg.lower()
                expect_protocol_value = False
                i += 1
                continue
            
            if expect_mode_value:
                parsed.mode = arg.lower()
                expect_mode_value = False
                i += 1
                continue
            
            if expect_wake_mac:
                parsed.wake = arg
                expect_wake_mac = False
                i += 1
                continue
                
            if expect_add_name:
                parsed.add_device = arg
                expect_add_name = False
                i += 1
                continue
                
            if expect_remove_name:
                parsed.remove_device = arg
                expect_remove_name = False
                i += 1
                continue
                
            if expect_register_name:
                parsed.register_device = arg
                expect_register_name = False
                i += 1
                continue
            
            if expect_update_name:
                parsed.update_device = arg
                expect_update_name = False
                i += 1
                continue
            
            # Handle keyword parameters (set expectation for next arg)
            if lower_arg == 'port':
                expect_port_value = True
                i += 1
                continue
            
            if lower_arg == 'token':
                expect_token_value = True
                i += 1
                continue
            
            if lower_arg == 'ip':
                expect_ip_value = True
                i += 1
                continue
            
            if lower_arg in ['device-id', 'deviceid']:
                expect_device_id_value = True
                i += 1
                continue
            
            if lower_arg in ['api-token', 'apitoken']:
                expect_api_token_value = True
                i += 1
                continue
            
            if lower_arg in ['http-url', 'httpurl']:
                expect_http_url_value = True
                i += 1
                continue
            
            if lower_arg in ['wss-url', 'wssurl']:
                expect_wss_url_value = True
                i += 1
                continue
            
            if lower_arg == 'protocol':
                expect_protocol_value = True
                i += 1
                continue
            
            # Mode switch for on-the-fly transport selection (tcp/http/wss)
            if lower_arg == 'mode':
                expect_mode_value = True
                i += 1
                continue
            
            # Direct mode shortcuts (without 'mode' keyword)
            if lower_arg in ['tcp', 'http', 'wss', 'local', 'cloud']:
                if lower_arg == 'local':
                    parsed.mode = 'tcp'
                elif lower_arg == 'cloud':
                    parsed.mode = 'http'
                else:
                    parsed.mode = lower_arg
                i += 1
                continue
            
            # Auto-detect URL by scheme
            if any(arg.startswith(scheme) for scheme in self.URL_SCHEMES):
                parsed.url = arg
                i += 1
                continue
            
            # Handle commands supplied without -- prefix
            cmd = self.COMMAND_MAP.get(lower_arg)
            if cmd:
                if cmd == 'wake':
                    expect_wake_mac = True
                    setattr(parsed, 'wake', None)  # Initialize placeholder
                elif cmd == 'add_device':
                    expect_add_name = True
                elif cmd == 'remove_device':
                    expect_remove_name = True
                elif cmd == 'register_device':
                    expect_register_name = True
                elif cmd == 'update_device':
                    expect_update_name = True
                else:
                    setattr(parsed, cmd, True)
                i += 1
                continue
            
            # If the token matches a saved device name
            if not getattr(parsed, 'device', None) and self.dev_mgr.get(arg):
                parsed.device = arg
                i += 1
                continue
            
            # If it looks like an IP address (simple heuristic)
            if '.' in arg and not getattr(parsed, 'ip', None):
                parsed.ip = arg
                i += 1
                continue
                
            # If it looks like a port number
            if arg.isdigit() and not getattr(parsed, 'port', None):
                parsed.port = int(arg)
                i += 1
                continue
                
            # If it appears to be a device token (long string)
            if len(arg) > 20 and not getattr(parsed, 'token', None):
                parsed.token = arg
                i += 1
                continue
                
            # If it resembles a device ID
            if (arg.startswith('WL') or len(arg) > 8) and not getattr(parsed, 'device_id', None):
                parsed.device_id = arg
                i += 1
                continue
            
            # Treat as an unknown argument for argparse later
            remaining.append(arg)
            i += 1
        
        # Parse the collected arguments with argparse
        try:
            flag_args, _ = self.parser.parse_known_args(remaining)
            for k, v in vars(flag_args).items():
                # Only set if value is meaningful AND not already set
                if v not in [None, False, []] and not hasattr(parsed, k):
                    setattr(parsed, k, v)
        except SystemExit:
            return argparse.Namespace(help=True)
        
        # Verify that a command is specified for the targeted device
        if hasattr(parsed, 'device') and parsed.device:
            if not self._has_device_command(parsed):
                if not any(getattr(parsed, x, False) for x in [
                    'add_device', 'remove_device', 'list_devices', 'cloud_list_devices', 'help', 
                    'register_device', 'delete_device', 'update_device'
                ]):
                    self.printer.print_error(f"Device '{parsed.device}' specified but no command given")
                    self.printer.print_info("Usage: wl DEVICE COMMAND")
                    return argparse.Namespace(help=True)
        
        return parsed
    
    def _has_device_command(self, parsed) -> bool:
        return any(getattr(parsed, cmd, False) for cmd in [
            'ping', 'info', 'wake', 'restart', 'ota_start', 'open_setup',
            'enable_site', 'disable_site', 'site_status', 'crypto_info',
            'update_token', 'enable_cloud', 'disable_cloud', 'cloud_status'
        ])
    
    @staticmethod
    def show_help():
        print("""
\033[1;36mWakeLink Client v1.0\033[0m

\033[1;32mBASIC USAGE:\033[0m
  \033[33mwl DEVICE COMMAND\033[0m
        → Execute command on device
        Example: wl pico ping

  \033[33mwl DEVICE wake MAC\033[0m
        → Send Wake-on-LAN
        Example: wl pico wake 00:11:22:33:44:55

\033[1;32mDEVICE MANAGEMENT:\033[0m
  \033[33mwl add NAME token TOKEN ip IP [port PORT]\033[0m
        → Add TCP device (local network)
        Example: wl add pico token abc123 ip 192.168.1.50

  \033[33mwl add NAME token TOKEN http-url URL wss-url URL [api-token TOKEN]\033[0m
        → Add Cloud device with separate HTTP and WSS URLs
        Example: wl add pico token abc123 http-url https://server.com wss-url wss://server.com

  \033[33mwl register NAME device-id ID api-token TOKEN [token TOKEN]\033[0m
        → Register cloud device on server (token auto-loaded if device exists)
        Example: wl register pico device-id WL123 api-token sk-xxx

  \033[33mwl list\033[0m
        → List configured devices

  \033[33mwl update NAME field VALUE [field VALUE ...]\033[0m
        → Update device fields (ip, token, port, http-url, wss-url, device-id, api-token, protocol)
        Example: wl update pico ip 192.168.1.100
        Example: wl update pico http-url https://new-server.com

  \033[33mwl remove NAME\033[0m
        → Remove device

\033[1;32mDEVICE COMMANDS:\033[0m
  ping, info, wake MAC, restart, ota, setup,
  site-on, site-off, site-status, crypto, update-token,
  cloud-on, cloud-off, cloud-status

\033[1;32mTRANSPORT MODES:\033[0m
  LOCAL (TCP)  → ip 192.168.1.50 (direct connection on port 99)
  HTTP         → http-url https://... (push/pull relay)
  WSS          → wss-url wss://... (WebSocket real-time)

\033[1;32mON-THE-FLY MODE SWITCH:\033[0m
  \033[33mwl DEVICE COMMAND tcp\033[0m     → Force local TCP mode
  \033[33mwl DEVICE COMMAND http\033[0m    → Force HTTP cloud mode  
  \033[33mwl DEVICE COMMAND wss\033[0m     → Force WSS cloud mode
  
  Examples:
    wl pico ping tcp          # Use TCP even if cloud is configured
    wl pico info http         # Use HTTP relay
    wl pico info wss          # Use WebSocket

\033[1;32mEXAMPLES:\033[0m
  wl add pico token TOKEN ip 192.168.1.50
  wl add pico token TOKEN http-url https://wakelink.deadboizxc.org wss-url wss://wakelink.deadboizxc.org
  wl register pico device-id WL123 api-token sk-xxx
  wl pico ping
  wl pico info http           # Switch to HTTP on the fly
  wl pico ping wss            # Switch to WSS on the fly
  wl list

\033[1;35mTIPS:\033[0m
• tcp/http/wss after command = one-time mode override (doesn't change config)
• http-url for HTTP polling, wss-url for WebSocket - can use different servers
• WSS requires: pip install websocket-client
• Default URLs: https://wakelink.deadboizxc.org | wss://wakelink.deadboizxc.org
""")


# =============================
# WakeLink Client
# =============================
class WakeLinkClient:
    """Main WakeLink client for executing commands on devices.
    
    Handles device resolution, transport selection (TCP/Cloud),
    and command execution with proper error handling.
    
    Attributes:
        dev_mgr: DeviceManager for loading/saving device configs.
        printer: OutputPrinter for formatted output.
        session: requests.Session for HTTP API calls.
        base_url: Cloud server base URL.
    
    Supported Operations:
        - Device commands: ping, info, wake, restart, ota, etc.
        - Device management: add, remove, list
        - Cloud operations: register, delete, cloud-list
    """
    
    def __init__(self):
        """Initialize WakeLink client with device manager and HTTP session."""
        self.dev_mgr = DeviceManager()
        self.printer = OutputPrinter()
        
        # Configure HTTP session with retry logic
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        
        # Cloud server URL (from constants)
        self.base_url = DEFAULT_HTTP_URL

    def _api_request(self, method: str, endpoint: str, api_token: str, json_data=None):
        """Make authenticated HTTP request to cloud API.
        
        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path (e.g., /api/devices).
            api_token: Bearer token for authentication.
            json_data: Optional JSON body for POST requests.
            
        Returns:
            Response JSON dict on success, None on error.
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        
        try:
            resp = self.session.request(method, url, headers=headers, json=json_data, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            self.printer.print_error(f"API error: {e}")
            # Show server response details if available
            if hasattr(e, 'response') and e.response is not None:
                try:
                    print(f"  Server: {e.response.json()}")
                except:
                    print(f"  Status: {e.response.status_code}")
            return None

    def _handle_register(self, name: str, device_id: str, device_token: str, api_token: str):
        """Register a new device with the cloud server.
        
        Creates device record on server using the provided device token.
        The device token must match the token on the physical device.
        
        Args:
            name: Local device name for reference.
            device_id: Unique device identifier for cloud.
            device_token: Device token (must match firmware token).
            api_token: API authentication token.
        """
        self.printer.print_header(f"REGISTER: {name}")
        
        # Call cloud API to register device with the provided token
        data = {
            "device_id": device_id,
            "device_data": {
                "name": name,
                "device_token": device_token  # Pass the token to server
            }
        }
        result = self._api_request("POST", "/api/register_device", api_token, json_data=data)
        
        if not result or result.get("status") != "device_registered":
            self.printer.print_error("Registration failed")
            return
        
        # Save device locally with all cloud configuration (uses defaults from constants)
        self.dev_mgr.add(
            name=name, 
            token=device_token,
            port=DEFAULT_PORT,
            cloud=True, 
            device_id=device_id,
            http_url=DEFAULT_HTTP_URL,
            wss_url=DEFAULT_WSS_URL,
            protocol=DEFAULT_PROTOCOL,
            api_token=api_token
        )
        self.printer.print_device_added(
            name=name,
            token=device_token,
            device_id=device_id,
            cloud=True
        )
        self.printer.print_info(f"HTTP URL: {DEFAULT_HTTP_URL}")
        self.printer.print_info(f"WSS URL: {DEFAULT_WSS_URL}")
        self.printer.print_info(f"Protocol: {DEFAULT_PROTOCOL.upper()}")
        self.printer.print_info("To switch: wl <name> <cmd> http|wss")

    def _handle_delete(self, name: str, api_token: str):
        """Delete a cloud device from server and local config.
        
        Args:
            name: Local device name to delete.
            api_token: API authentication token.
        """
        self.printer.print_header(f"DELETE: {name}")
        
        # Find device in local config
        saved = self.dev_mgr.get(name)
        if not saved or not saved.get("cloud"):
            self.printer.print_error(f"Cloud device '{name}' not found")
            return
        
        # Delete from cloud server
        data = {"device_token": saved["token"]}
        result = self._api_request("POST", "/api/delete_device", api_token, json_data=data)
        
        if result and result.get("status") == "device_deleted":
            # Remove from local config
            self.dev_mgr.remove(name)
            self.printer.print_success(f"Device '{name}' deleted from cloud & local")
        else:
            self.printer.print_error("Failed to delete")

    def _handle_cloud_list(self, api_token: str):
        """List all devices registered on the cloud server.
        
        Args:
            api_token: API authentication token.
        """
        self.printer.print_header("CLOUD DEVICES")
        
        result = self._api_request("GET", "/api/devices", api_token)
        if not result:
            return
        
        # Display user info
        print(f"User: {result['user']} | Plan: {result['plan']} | Limit: {result['devices_limit']}\n")
        
        # Display each device with status
        for dev in result['devices']:
            status = "ONLINE" if dev['online'] else "OFFLINE"
            color = 'green' if dev['online'] else 'red'
            print(f"  {self.printer.colorize('●', color)} {dev['device_id']}")
            print(f"     Token: {dev['device_token'][:8]}...{dev['device_token'][-4:]}")
            print(f"     Last: {dev['last_seen'] or 'never'} | Polls: {dev['poll_count']}")
            print()

    def _resolve_device(self, args):
        """Resolve device name to full device configuration.
        
        Looks up device in saved configs and merges with any
        command-line overrides.
        
        Args:
            args: Parsed command-line arguments.
            
        Returns:
            Device config dict or None if not found.
        """
        if not getattr(args, 'device', None):
            return None
        
        # Look up saved device
        saved = self.dev_mgr.get(args.device)
        if not saved:
            self.printer.print_error(f"Device '{args.device}' not found")
            return None
        
        # Make a copy and ensure device_id is set
        dev = saved.copy()
        dev["device_id"] = dev.get("device_id", args.device)
        self.printer.print_success(f"Using saved device: {args.device}")
        return dev

    def run(self, args):
        """Execute command based on parsed arguments.
        
        Routes to appropriate handler based on command type:
        - Help: Show usage information
        - Device management: add/remove/list devices
        - Cloud operations: register/delete/cloud-list
        - Device commands: ping/info/wake/restart/etc.
        
        Args:
            args: Parsed Namespace from SmartParser.
        """
        # === HELP ===
        if getattr(args, 'help', False):
            SmartParser.show_help()
            return

        # === REGISTER DEVICE ===
        if getattr(args, 'register_device', None):
            api_token = getattr(args, 'api_token', None)
            device_token = getattr(args, 'token', None)
            device_id = getattr(args, 'device_id', None)
            
            # Try to get token from saved device if not provided
            if not device_token:
                saved = self.dev_mgr.get(args.register_device)
                if saved and saved.get('token'):
                    device_token = saved['token']
                    self.printer.print_info(f"Using token from saved device '{args.register_device}'")
            
            if not api_token:
                self.printer.print_error("api-token required")
                return
            if not device_token:
                self.printer.print_error("token required (device access token)")
                self.printer.print_info("Hint: Add device first with 'wl add NAME token TOKEN ip IP' or provide 'token TOKEN'")
                return
            if not device_id:
                self.printer.print_error("device-id required")
                return
            
            self._handle_register(args.register_device, device_id, device_token, api_token)
            return

        # === DELETE DEVICE ===
        if getattr(args, 'delete_device', None):
            api_token = getattr(args, 'api_token', None)
            if not api_token:
                self.printer.print_error("api-token required")
                return
            self._handle_delete(args.delete_device, api_token)
            return

        # === CLOUD LIST ===
        if getattr(args, 'cloud_list_devices', False):
            api_token = getattr(args, 'api_token', None)
            if not api_token:
                self.printer.print_error("api-token required")
                return
            self._handle_cloud_list(api_token)
            return

        # === ADD DEVICE ===
        if getattr(args, 'add_device', None):
            if not getattr(args, 'token', None):
                self.printer.print_error("token required")
                return
            
            http_url = getattr(args, 'http_url', None)
            wss_url = getattr(args, 'wss_url', None)
            ip = getattr(args, 'ip', None)
            protocol = getattr(args, 'protocol', None)
            
            # Determine mode based on URL or IP
            if http_url or wss_url:
                is_cloud = True
                # Auto-detect protocol if not specified
                if not protocol:
                    protocol = 'http'
            else:
                is_cloud = False
                if not ip:
                    self.printer.print_error("ip or http-url/wss-url required")
                    return
            
            device_id = getattr(args, 'device_id', None) or args.add_device
            
            self.dev_mgr.add(
                name=args.add_device,
                ip=ip,
                token=args.token,
                port=getattr(args, 'port', DEFAULT_PORT),
                cloud=is_cloud,
                device_id=device_id,
                http_url=http_url,
                wss_url=wss_url,
                api_token=getattr(args, 'api_token', None),
                protocol=protocol
            )
            
            # Print confirmation
            if is_cloud:
                mode_str = "WSS" if protocol == "wss" else "HTTP"
                print(f"✅ Device '{args.add_device}' added ({mode_str})")
                if http_url:
                    print(f"  🔗 HTTP URL: {http_url}")
                if wss_url:
                    print(f"  🔗 WSS URL: {wss_url}")
                if protocol:
                    print(f"  📡 Protocol: {protocol.upper()}")
            else:
                print(f"✅ Device '{args.add_device}' added (LOCAL)")
                print(f"  🌐 IP: {ip}:{getattr(args, 'port', DEFAULT_PORT)}")
            
            print(f"  🔐 Token: {args.token[:8]}...{args.token[-4:]}")
            if device_id and device_id != args.add_device:
                print(f"  🆔 Device ID: {device_id}")
            return

        # === UPDATE DEVICE ===
        if getattr(args, 'update_device', None):
            device_name = args.update_device
            existing = self.dev_mgr.get(device_name)
            if not existing:
                self.printer.print_error(f"Device '{device_name}' not found")
                return
            
            # Collect fields to update (only non-None values)
            # Special value "none" or "clear" removes the field
            updates = {}
            clears = []
            
            ip_val = getattr(args, 'ip', None)
            if ip_val:
                if ip_val.lower() in ('none', 'clear', '-'):
                    clears.append('ip')
                else:
                    updates['ip'] = ip_val
            
            token_val = getattr(args, 'token', None)
            if token_val:
                updates['token'] = token_val
            
            port_val = getattr(args, 'port', None)
            if port_val is not None:
                if port_val == 0:  # 0 means clear
                    clears.append('port')
                else:
                    updates['port'] = port_val
            
            http_url_val = getattr(args, 'http_url', None)
            if http_url_val:
                if http_url_val.lower() in ('none', 'clear', '-'):
                    clears.append('http_url')
                else:
                    updates['http_url'] = http_url_val
            
            wss_url_val = getattr(args, 'wss_url', None)
            if wss_url_val:
                if wss_url_val.lower() in ('none', 'clear', '-'):
                    clears.append('wss_url')
                else:
                    updates['wss_url'] = wss_url_val
            
            device_id_val = getattr(args, 'device_id', None)
            if device_id_val:
                updates['device_id'] = device_id_val
            
            api_token_val = getattr(args, 'api_token', None)
            if api_token_val:
                if api_token_val.lower() in ('none', 'clear', '-'):
                    clears.append('api_token')
                else:
                    updates['api_token'] = api_token_val
            
            protocol_val = getattr(args, 'protocol', None)
            if protocol_val:
                if protocol_val.lower() in ('none', 'clear', '-'):
                    clears.append('protocol')
                else:
                    updates['protocol'] = protocol_val
            
            if not updates and not clears:
                self.printer.print_error("No fields to update. Usage: wl update NAME field VALUE ...")
                self.printer.print_info("Fields: ip, token, port, http-url, wss-url, device-id, api-token, protocol")
                self.printer.print_info("Use 'none' or 'clear' to remove a field: wl update NAME ip none")
                return
            
            # Apply updates via dev_mgr.update()
            if updates:
                self.dev_mgr.update(device_name, **updates)
            
            # Clear fields
            for field in clears:
                if field in self.dev_mgr.devices[device_name]:
                    del self.dev_mgr.devices[device_name][field]
            if clears:
                self.dev_mgr._save()
            
            print(f"✅ Device '{device_name}' updated:")
            for key, value in updates.items():
                if key == 'token':
                    print(f"  🔐 {key}: {value[:8]}...{value[-4:]}")
                else:
                    print(f"  → {key}: {value}")
            for field in clears:
                print(f"  🗑️ {field}: cleared")
            return

        # === REMOVE DEVICE ===
        if getattr(args, 'remove_device', None):
            device_name = args.remove_device
            if self.dev_mgr.get(device_name):
                self.dev_mgr.remove(device_name)
                self.printer.print_device_removed(device_name)
            else:
                self.printer.print_error(f"Device '{device_name}' not found")
            return

        # === LIST DEVICES ===
        if getattr(args, 'list_devices', False):
            devices = self.dev_mgr.list_devices()
            self.printer.print_device_list(devices)
            return

        # === DEVICE COMMANDS ===
        dev = self._resolve_device(args)
        if not dev or not dev.get("token"):
            self.printer.print_warning("No command - use 'wl help'")
            return

        # Choose the appropriate handler based on mode override or saved config
        # Backward compatibility: fallback to old 'url' field
        legacy_url = dev.get("url", "")
        http_url = dev.get("http_url", "")
        wss_url = dev.get("wss_url", "")
        
        # If new fields are empty, use legacy URL based on scheme
        if legacy_url and not http_url and not wss_url:
            if legacy_url.startswith(("wss://", "ws://")):
                wss_url = legacy_url
            else:
                http_url = legacy_url
        
        protocol = dev.get("protocol", "").lower()
        handler_kwargs = {"token": dev["token"], "device_id": dev["device_id"]}
        
        # Check for on-the-fly mode override (tcp/http/wss)
        mode_override = getattr(args, 'mode', None)
        
        if mode_override:
            # User specified mode on command line
            if mode_override == 'tcp':
                # Force TCP mode
                if not dev.get("ip"):
                    self.printer.print_error("TCP mode requires IP address. Add with: wl update <name> ip <IP>")
                    return
                handler_kwargs.update({"ip": dev["ip"], "port": dev.get("port", DEFAULT_PORT)})
                handler = TCPHandler(**handler_kwargs)
                mode = "LOCAL (forced)"
            elif mode_override == 'http':
                # Force HTTP mode
                url = http_url or DEFAULT_HTTP_URL
                handler_kwargs["base_url"] = url
                handler_kwargs["protocol"] = "http"
                if dev.get("api_token"):
                    handler_kwargs["api_token"] = dev["api_token"]
                handler = CloudClient(**handler_kwargs)
                mode = "HTTP (forced)"
            elif mode_override == 'wss':
                # Force WSS mode
                if not WEBSOCKET_AVAILABLE:
                    self.printer.print_warning("websocket-client not installed, using HTTP fallback")
                    url = http_url or DEFAULT_HTTP_URL
                    handler_kwargs["base_url"] = url
                    handler_kwargs["protocol"] = "http"
                    mode = "HTTP (WSS unavailable)"
                else:
                    url = wss_url or DEFAULT_WSS_URL
                    handler_kwargs["base_url"] = url
                    handler_kwargs["protocol"] = "wss"
                    mode = "WSS (forced)"
                if dev.get("api_token"):
                    handler_kwargs["api_token"] = dev["api_token"]
                handler = CloudClient(**handler_kwargs)
            else:
                self.printer.print_error(f"Unknown mode: {mode_override}. Use: tcp, http, wss")
                return
        elif http_url or wss_url:
            # Cloud mode - use protocol field to choose URL
            if not protocol:
                protocol = "http"  # Default to HTTP
            
            # Check WSS availability
            if protocol == "wss" and not WEBSOCKET_AVAILABLE:
                self.printer.print_warning("websocket-client not installed, using HTTP fallback")
                protocol = "http"
            
            # Select appropriate URL based on protocol
            if protocol == "wss":
                url = wss_url or DEFAULT_WSS_URL
            else:
                url = http_url or DEFAULT_HTTP_URL
            
            handler_kwargs["base_url"] = url
            handler_kwargs["protocol"] = protocol
            if dev.get("api_token"):
                handler_kwargs["api_token"] = dev["api_token"]
            
            handler = CloudClient(**handler_kwargs)
            mode = "WSS" if protocol == "wss" else "HTTP"
        else:
            # Local TCP handler
            if not dev.get("ip"):
                self.printer.print_error("Device has no IP address configured for TCP mode")
                self.printer.print_info("Add IP: wl update <name> ip <IP>")
                self.printer.print_info("Or use cloud: wl <name> <cmd> http")
                return
            handler_kwargs.update({"ip": dev["ip"], "port": dev.get("port", DEFAULT_PORT)})
            handler = TCPHandler(**handler_kwargs)
            mode = "LOCAL"
        self.printer.print_info(f"{mode} mode activated")

        # Execute commands on the resolved device
        client = WakeLinkCommands(handler)
        cmd_map = {
            "ping": client.ping_device,
            "wake": client.wake_device,
            "info": client.device_info,
            "restart": client.restart_device,
            "ota_start": client.ota_start,
            "open_setup": client.open_setup,
            "enable_site": client.enable_site,
            "disable_site": client.disable_site,
            "site_status": client.site_status,
            "enable_cloud": client.enable_cloud,
            "disable_cloud": client.disable_cloud,
            "cloud_status": client.cloud_status,
            "crypto_info": client.crypto_info,
            "update_token": client.update_token,
        }

        executed = False
        
        # Handle wake command separately
        if hasattr(args, 'wake') and args.wake:
            self.printer.print_command("wake", mode)
            try:
                result = client.wake_device(format_mac_address(args.wake))
                print(f"\n{self.printer.format_response(result)}")
                executed = True
            except Exception as e:
                self.printer.print_error(f"Wake failed: {e}")

        # Handle other commands
        for cmd, func in cmd_map.items():
            if cmd != "wake" and getattr(args, cmd, False):
                self.printer.print_command(cmd, mode)
                try:
                    result = func()
                    if result:
                        print(f"\n{self.printer.format_response(result)}")
                        
                        # Automatically update the saved token when the command succeeds
                        if cmd == "update_token" and result.get('status') == 'success' and 'new_token' in result:
                            new_token = result['new_token']
                            if dev and args.device:
                                # Persist the new token back to the saved configuration
                                self.dev_mgr.devices[args.device]['token'] = new_token
                                self.dev_mgr._save()
                                self.printer.print_success(f"Token updated in device configuration: {new_token[:16]}...")
                    
                    executed = True
                except Exception as e:
                    self.printer.print_error(f"Failed: {e}")
                break

        if not executed:
            self.printer.print_warning("No command - use 'wl help'")


# =============================
# Main Entry Point
# =============================
def main():
    """Main entry point for WakeLink CLI.
    
    Parses command-line arguments and executes the requested operation.
    Handles keyboard interrupt gracefully.
    """
    # Parse command-line arguments
    parser = SmartParser()
    args = parser.parse(sys.argv[1:])
    
    try:
        # Create client and execute command
        client = WakeLinkClient()
        client.run(args)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print(f"\n{OutputPrinter.colorize('Cancelled', 'yellow')}")
    except Exception as e:
        # Display any unhandled errors
        OutputPrinter.print_error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""Helper utilities for WakeLink Client.

This module provides utility functions for data validation and formatting
used throughout the WakeLink client application.

Functions:
    validate_mac_address: Check if MAC address format is valid.
    format_mac_address: Normalize MAC address to standard colon format.

Author: deadboizxc
Version: 1.0
"""

import re


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format.
    
    Checks if the provided string is a valid MAC address in either
    colon-separated (00:11:22:33:44:55) or hyphen-separated
    (00-11-22-33-44-55) format.
    
    Args:
        mac: MAC address string to validate.
        
    Returns:
        True if valid MAC address format, False otherwise.
        
    Examples:
        >>> validate_mac_address('00:11:22:33:44:55')
        True
        >>> validate_mac_address('00-11-22-33-44-55')
        True
        >>> validate_mac_address('invalid')
        False
    """
    # Pattern matches 6 groups of 2 hex digits separated by : or -
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac))


def format_mac_address(mac: str) -> str:
    """Normalize MAC address to standard colon-separated uppercase format.
    
    Accepts MAC addresses in various formats and converts to the
    standard format used by WakeLink firmware for WOL packets.
    
    Args:
        mac: MAC address in any common format.
        
    Returns:
        MAC address in format 'XX:XX:XX:XX:XX:XX' (uppercase).
        
    Raises:
        ValueError: If MAC address length is invalid after stripping.
        
    Examples:
        >>> format_mac_address('00:11:22:33:44:55')
        '00:11:22:33:44:55'
        >>> format_mac_address('00-11-22-33-44-55')
        '00:11:22:33:44:55'
        >>> format_mac_address('001122334455')
        '00:11:22:33:44:55'
    """
    # Remove all separators and convert to uppercase
    mac = mac.replace(':', '').replace('-', '').upper()
    
    # Validate length (12 hex characters = 6 bytes)
    if len(mac) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")
    
    # Insert colons every 2 characters
    return ':'.join(mac[i:i+2] for i in range(0, 12, 2))
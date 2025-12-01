/**
 * @file udp_handler.h
 * @brief UDP handler for Wake-on-LAN functionality.
 * 
 * Provides Wake-on-LAN (WOL) magic packet generation and transmission.
 * Uses standard WOL protocol:
 * - 6 bytes of 0xFF
 * - 16 repetitions of target MAC address
 * - Sent to broadcast address 255.255.255.255:9
 * 
 * @note Only outbound UDP is used; no listening required.
 * 
 * @author deadboizxc
 * @version 1.0
 */

#ifndef UDP_HANDLER_H
#define UDP_HANDLER_H

#include <Arduino.h>
#include "config.h"

/**
 * @brief Initialize UDP socket for WOL transmission.
 * 
 * Opens UDP socket on configured port. Does not bind for listening
 * as only outbound packets are needed.
 * 
 * @note Call once during setup() after WiFi is connected.
 */
void initUDP();

/**
 * @brief Send a Wake-on-LAN magic packet.
 * 
 * Constructs and broadcasts a standard WOL magic packet:
 * - Preamble: 6 bytes of 0xFF
 * - Target: MAC address repeated 16 times
 * - Destination: 255.255.255.255:9 (broadcast)
 * 
 * @param macStr MAC address in format "AA:BB:CC:DD:EE:FF" or "AA-BB-CC-DD-EE-FF".
 *               Delimiters are automatically stripped.
 * 
 * @note Logs success/failure to Serial.
 */
void sendWOL(const String& macStr);

#endif // UDP_HANDLER_H
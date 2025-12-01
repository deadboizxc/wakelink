/**
 * @file wifi_manager.h
 * @brief WiFi connection and AP mode management for WakeLink firmware.
 * 
 * Provides WiFi station mode connection, automatic reconnection,
 * and Access Point mode for device configuration.
 * 
 * Connection Flow:
 * 1. initWiFi() attempts to connect using saved credentials
 * 2. On success: device operates in STA mode
 * 3. On failure: device starts AP mode for configuration
 * 
 * AP Mode:
 * - SSID: WakeLink-Setup
 * - Password: configure123
 * - IP: 192.168.4.1
 * - Timeout: 5 minutes (then reboots)
 * 
 * @note handleWiFi() must be called in loop() for connection monitoring.
 * 
 * @author deadboizxc
 * @version 1.0
 */

#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include "config.h"

/**
 * @brief Initialize WiFi connection.
 * 
 * Attempts to connect to saved credentials if available.
 * Blocks for up to 10 seconds during connection attempt.
 * Falls back to AP mode on failure or missing configuration.
 * 
 * @note Call once during setup().
 */
void initWiFi();

/**
 * @brief Handle WiFi state in main loop.
 * 
 * Performs periodic tasks based on current mode:
 * - AP mode: Monitors portal timeout, triggers reboot after 5 minutes
 * - STA mode: Checks connection every 30s, attempts reconnection
 * 
 * @note Call from loop() every iteration.
 */
void handleWiFi();

/**
 * @brief Start Access Point for configuration.
 * 
 * Switches the module to AP mode with predefined SSID/password.
 * Updates global state flags (inAPMode, apModeStartTime).
 * Outputs connection hints to Serial.
 * 
 * @note Used internally by initWiFi() and handleWiFi().
 */
void startAP();

/**
 * @brief Check if device is currently in Access Point mode.
 * 
 * @return true if in AP mode, false if in STA mode.
 */
bool isInAPMode();

#endif // WIFI_MANAGER_H
/**
 * @file ota_manager.h
 * @brief Over-The-Air update manager for WakeLink firmware.
 * 
 * Provides OTA update functionality using Arduino OTA library.
 * Allows firmware updates via WiFi from Arduino IDE or other
 * compatible upload tools.
 * 
 * OTA Configuration:
 * - Hostname: WakeLink (discoverable via mDNS)
 * - Password: wakelink123
 * - Port: Standard Arduino OTA port
 * 
 * OTA Mode:
 * - Triggered via "ota_start" command
 * - 30-second window for upload
 * - LED blinks during OTA mode
 * - UDP stopped to free resources
 * 
 * @note handleOTA() must be called in loop() for OTA to work.
 * 
 * @author deadboizxc
 * @version 1.0
 */

#ifndef OTA_MANAGER_H
#define OTA_MANAGER_H

#include "config.h"

/**
 * @brief Initialize Arduino OTA subsystem.
 * 
 * Sets hostname, password, and registers start/end callbacks.
 * Must be called during setup() after WiFi connected.
 */
void initOTA();

/**
 * @brief Handle OTA update requests.
 * 
 * Processes any pending OTA traffic. Must be called from loop()
 * every iteration for OTA to function.
 */
void handleOTA();

/**
 * @brief Enter OTA update mode.
 * 
 * Enables OTA mode for 30-second window:
 * - Sets otaMode flag
 * - Records start time
 * - Stops UDP to free resources
 * - Blinks LED for visual indication
 * 
 * Called by "ota_start" command handler.
 */
void enterOTAMode();

#endif // OTA_MANAGER_H
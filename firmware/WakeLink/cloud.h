/**
 * @file cloud.h
 * @brief Cloud communication module for WakeLink firmware.
 * 
 * Unified WSS client for real-time cloud relay communication.
 * Handles WebSocket connection, packet processing, and command routing.
 * 
 * Transport Architecture:
 * - TCP (port 99): Local network access (always active)
 * - WSS: Cloud relay (real-time bidirectional)
 * 
 * @note Server acts as transparent relay and never decrypts payload.
 *       API token sent via query param and headers for Cloudflare compatibility.
 */

#ifndef CLOUD_H
#define CLOUD_H

#include <Arduino.h>
#include <WebSocketsClient.h>
#include "config.h"

/**
 * @brief Initialize cloud module.
 * 
 * Parses cloud_url from config and establishes WSS connection.
 * Call once during setup() after config is loaded.
 * 
 * @note Automatically converts http:// to ws:// and https:// to wss://
 */
void initCloud();

/**
 * @brief Process cloud events in main loop.
 * 
 * Handles WSS connection maintenance, incoming packets, and heartbeat.
 * Must be called frequently from loop().
 */
void handleCloud();

/**
 * @brief Push a command to cloud server.
 * 
 * Creates signed packet and sends via WSS.
 * 
 * @param command Command name string.
 * @param data Command parameters as JSON object.
 */
void pushCloud(const String& command, const JsonObject& data);

/**
 * @brief Send response packet to cloud.
 * 
 * Routes response back through WSS connection.
 * 
 * @param response_packet Signed JSON response packet.
 */
void sendCloudResponse(const String& response_packet);

/**
 * @brief Check cloud connection status.
 * 
 * @return true if WSS connected, false otherwise.
 */
bool isCloudConnected();

/**
 * @brief Get cloud status string.
 * 
 * @return "connected", "disconnected", or "disabled".
 */
String getCloudStatus();

/**
 * @brief Enable cloud mode.
 * 
 * Saves cloud_enabled flag to config and initializes WSS connection.
 */
void enableCloud();

/**
 * @brief Disable cloud mode.
 * 
 * Disconnects WSS and saves cloud_enabled flag to config.
 */
void disableCloud();

/**
 * @brief Check if cloud mode is enabled in config.
 * 
 * @return true if cloud_enabled flag is set.
 */
bool isCloudEnabled();

#endif // CLOUD_H

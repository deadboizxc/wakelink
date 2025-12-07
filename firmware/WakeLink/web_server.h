/**
 * @file web_server.h
 * @brief HTTP web server interface for WakeLink configuration.
 * 
 * Provides a web-based configuration interface for initial device setup.
 * Active primarily in AP mode, allows users to configure:
 * - WiFi credentials (SSID/password)
 * - Device token for encryption
 * - Cloud server settings
 * 
 * Routes:
 * - GET /       : Main configuration page
 * - POST /save  : Save settings and reboot
 * - GET /scan   : WiFi network scan
 * - GET /reset  : Factory reset confirmation
 * - POST /reset : Perform factory reset
 * 
 * @note Web server can be enabled/disabled via web_control command.
 * 
 * @author deadboizxc
 * @version 1.0
 */

#ifndef WEB_SERVER_H
#define WEB_SERVER_H

#include <Arduino.h>
#include "config.h"
#include "CryptoManager.h"

/// @brief Global crypto manager instance (defined in WakeLink.ino)
extern CryptoManager crypto;

/// @brief Global web server instance (defined in config.cpp)
extern WebServerType server;

/// @brief Web server enabled flag (can be toggled via command)
extern bool webServerEnabled;

/**
 * @brief Initialize web server routes and start listening.
 * 
 * Registers all HTTP handlers and starts the server on port 80.
 * Should be called during setup() after WiFi initialization.
 */
void initWebServer();

#endif // WEB_SERVER_H
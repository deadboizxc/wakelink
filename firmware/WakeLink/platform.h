/**
 * @file platform.h
 * @brief Platform abstraction layer for ESP8266/ESP32.
 * 
 * Provides unified API across ESP8266 and ESP32 platforms.
 * Handles differences in:
 * - WiFi libraries and APIs
 * - Web server types
 * - Chip ID retrieval
 * - Client acceptance methods
 * - WiFi encryption type checks
 * 
 * Also defines common constants used throughout firmware:
 * - Pin assignments (STATUS_LED, RESET_BUTTON)
 * - Network ports (TCP, UDP)
 * - AP configuration (SSID, password, timeout)
 * - EEPROM size
 * - OTA settings
 * 
 * @author deadboizxc
 * @version 1.0
 */

#pragma once

// ============================================
// Platform-specific includes and definitions
// ============================================

#ifdef ESP8266
  #include <ESP8266WiFi.h>
  #include <ESP8266WebServer.h>
  #include <ESP8266HTTPClient.h>
  #include <ESP8266mDNS.h>
  #include <ArduinoOTA.h>
  
  /// @brief Web server type alias for ESP8266
  #define WebServerType ESP8266WebServer

  /**
   * @brief Get unique chip identifier.
   * @return Hex string of ESP8266 chip ID.
   */
  inline String getChipId() { return String(ESP.getChipId(), HEX); }
  
  /**
   * @brief Accept client from server (ESP8266 style).
   * @param server WiFiServer instance.
   * @return WiFiClient if available, empty otherwise.
   */
  inline WiFiClient getServerClient(WiFiServer& server) { return server.available(); }
  
  /**
   * @brief Check if network is encrypted.
   * @param i Network index from scan.
   * @return true if encrypted, false if open.
   */
  inline bool isNetworkEncrypted(int i) { return WiFi.encryptionType(i) != ENC_TYPE_NONE; }

#else  // ESP32
  #include <WiFi.h>
  #include <WebServer.h>
  #include <HTTPClient.h>
  #include <ESPmDNS.h>
  #include <ArduinoOTA.h>
  
  /// @brief Web server type alias for ESP32
  #define WebServerType WebServer

  /**
   * @brief Get unique chip identifier.
   * @return Hex string of ESP32 MAC address (lower 32 bits).
   */
  inline String getChipId() {
    return String((uint32_t)ESP.getEfuseMac(), HEX);
  }
  
  /**
   * @brief Accept client from server (ESP32 style).
   * @param server WiFiServer instance.
   * @return WiFiClient if available, empty otherwise.
   */
  inline WiFiClient getServerClient(WiFiServer& server) { return server.accept(); }
  
  /**
   * @brief Check if network is encrypted.
   * @param i Network index from scan.
   * @return true if encrypted, false if open.
   */
  inline bool isNetworkEncrypted(int i) { return WiFi.encryptionType(i) != WIFI_AUTH_OPEN; }
#endif

// ============================================
// Common includes
// ============================================

#include <WiFiUdp.h>
#include <WiFiClientSecure.h>
#include <EEPROM.h>
#include <ArduinoJson.h>

// ============================================
// Hardware Pin Definitions
// ============================================

/// @brief Status LED GPIO pin (built-in LED on most ESP modules)
#define STATUS_LED 2

/// @brief Factory reset button GPIO pin (BOOT button on most ESP modules)
#define RESET_BUTTON_PIN 0

// ============================================
// Network Constants
// ============================================

/// @brief TCP server port for local communication
#define TCP_PORT 99

/// @brief UDP port for Wake-on-LAN packets
#define UDP_PORT 9

// ============================================
// Access Point Configuration
// ============================================

/// @brief Default AP SSID for configuration mode
#define CONFIG_AP_SSID "WakeLink-Setup"

/// @brief Default AP password for configuration mode
#define CONFIG_AP_PASS "configure123"

/// @brief AP mode timeout in milliseconds (5 minutes)
#define CONFIG_PORTAL_TIMEOUT 300000UL

// ============================================
// Storage Constants
// ============================================

/// @brief EEPROM size for configuration storage
#define EEPROM_SIZE 1024

// ============================================
// OTA Update Constants
// ============================================

/// @brief mDNS hostname for OTA discovery
#define OTA_HOSTNAME "WakeLink"

/// @brief Password for OTA authentication
#define OTA_PASSWORD "wakelink123"

// ============================================
// Utility Functions
// ============================================

/**
 * @brief Configure TLS client with insecure mode.
 * 
 * Disables certificate validation for WiFiClientSecure.
 * Required for connecting to servers with self-signed certificates
 * or when certificate chain is not available.
 * 
 * @warning Use only in controlled environments.
 * 
 * @param client Reference to WiFiClientSecure to configure.
 */
inline void setupSecureClient(WiFiClientSecure& client) {
  client.setInsecure();
}
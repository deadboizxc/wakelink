/**
 * @file config.h
 * @brief Device configuration structure and global state for WakeLink.
 * 
 * Defines the DeviceConfig structure stored in EEPROM and declares
 * all global variables used across firmware modules.
 * 
 * EEPROM Layout:
 * - Bytes 0-383: DeviceConfig structure
 * - Bytes 384-385: Validity marker (0xAA, 0xBB)
 * - Bytes 386-389: Request counter (uint32_t)
 * 
 * Configuration Fields:
 * - device_token: 128-char secret for encryption key derivation
 * - wifi_ssid/wifi_pass: Network credentials
 * - device_id: Unique device identifier (e.g., WL12AB)
 * - server_url: Cloud server URL for WSS/HTTP
 * - cloud_api_token: API authentication token
 * - Flags: wifi_configured, cloud_enabled, initialized, web_server_enabled
 * 
 * @author deadboizxc
 * @version 1.0
 */

#pragma once
#include "platform.h"

/**
 * @brief Device configuration structure.
 * 
 * Stored in EEPROM and loaded at boot. Contains all persistent
 * settings needed for device operation.
 */
struct DeviceConfig {
    char device_token[128];      ///< Secret token for ChaCha20/HMAC key derivation
    char wifi_ssid[32];          ///< WiFi network SSID
    char wifi_pass[64];          ///< WiFi network password
    char device_id[24];          ///< Unique device identifier (e.g., WL12AB)
    char cloud_url[128];         ///< Cloud server URL (wss://...)
    char cloud_api_token[128];   ///< API token for cloud authentication
    uint8_t wifi_configured;     ///< 1 if WiFi credentials are set
    uint8_t cloud_enabled;       ///< 1 if cloud communication enabled (auto if URL set)
    uint8_t initialized;         ///< 1 if device has been initialized
    uint8_t web_server_enabled;  ///< 1 if web config server is enabled
    uint8_t _pad[4];             ///< Padding for alignment
};

// =============================
// Global Variables (extern declarations)
// =============================

extern DeviceConfig cfg;          ///< Device configuration instance
extern WiFiUDP udp;               ///< UDP socket for WOL packets
extern WiFiServer tcpServer;      ///< TCP server instance
extern WiFiClientSecure clientSecure; ///< Secure client for HTTPS/WSS
extern WebServerType server;      ///< HTTP web server instance
extern unsigned long lastCloudPoll; ///< Last cloud poll timestamp
extern bool inAPMode;             ///< True if in Access Point mode
extern unsigned long apModeStartTime; ///< AP mode start timestamp
extern bool otaMode;              ///< True if in OTA update mode
extern unsigned long otaStartTime; ///< OTA mode start timestamp
extern String DEVICE_TOKEN;       ///< Device token as String
extern String DEVICE_ID;          ///< Device ID as String
extern bool webServerEnabled;     ///< Web server enabled flag

// =============================
// Configuration Functions
// =============================

/**
 * @brief Load configuration from EEPROM.
 * 
 * Reads DeviceConfig from EEPROM and validates.
 * If invalid, initializes with defaults and generates device ID/token.
 */
void loadConfig();

/**
 * @brief Save configuration to EEPROM.
 * 
 * Writes DeviceConfig to EEPROM and sets validity marker.
 * 
 * @return true on successful commit, false on failure.
 */
bool saveConfig();

// =============================
// Utility Functions
// =============================

/**
 * @brief Blink the status LED.
 * 
 * Useful for visual feedback during operations.
 * 
 * @param times Number of blink cycles.
 * @param ms Delay in milliseconds between on/off states.
 */
void blink(int times, int ms);

/**
 * @brief Convert hexadecimal character to integer.
 * 
 * @param c Hex character ('0'-'9', 'a'-'f', 'A'-'F').
 * @return Integer value 0-15, or 0 for invalid input.
 */
uint8_t hex_char_to_int(char c);
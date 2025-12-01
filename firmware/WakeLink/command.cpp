/**
 * @file command.cpp
 * @brief Command execution handlers for WakeLink firmware.
 *
 * This file contains the implementation of all command handlers that can be
 * executed by external clients via TCP, HTTP, or WSS transports.
 */

#include "command.h"
#include "udp_handler.h"
#include "ota_manager.h"
#include "wifi_manager.h"
#include "CryptoManager.h"
#include "cloud.h"
#include "platform.h"

extern CryptoManager crypto;
extern bool webServerEnabled;

// Variables for asynchronous restart
unsigned long CommandManager::scheduledRestartTime = 0;
bool CommandManager::restartScheduled = false;

/**
 * @brief Ping command handler.
 *
 * Simple test command that returns "pong".
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_ping(JsonDocument& doc, JsonObject data) {
    doc["status"] = "success";
    doc["result"] = "pong";
}

/**
 * @brief Wake-on-LAN command handler.
 *
 * Sends WOL packet to the specified MAC address.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data containing "mac" field.
 */
void CommandManager::cmd_wake(JsonDocument& doc, JsonObject data) {
    const char* mac = data["mac"];
    if (!mac) {
        doc["status"] = "error";
        doc["error"] = "MAC_ADDRESS_REQUIRED";
    } else {
        sendWOL(String(mac));
        doc["status"] = "success";
        doc["result"] = "wol_sent";
        doc["mac"] = mac;
    }
}

/**
 * @brief Device info command handler.
 *
 * Returns diagnostic information including device ID, IP, SSID, RSSI,
 * crypto status, etc.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_info(JsonDocument& doc, JsonObject data) {
    doc["status"] = "success";
    doc["device_id"] = DEVICE_ID;
    doc["ip"] = WiFi.localIP().toString();
    doc["ssid"] = WiFi.SSID();
    doc["rssi"] = WiFi.RSSI();
    doc["requests"] = crypto.getRequestCount();
    doc["crypto_enabled"] = crypto.isEnabled();
    doc["mode"] = (WiFi.getMode() == WIFI_AP ? "AP" : "STA");
    doc["web_enabled"] = webServerEnabled;
    doc["cloud_enabled"] = cfg.cloud_enabled;
    doc["cloud_status"] = getCloudStatus();
    doc["free_heap"] = ESP.getFreeHeap();
}

/**
 * @brief Restart command handler.
 *
 * Schedules an immediate restart (in 1ms) and returns confirmation.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_restart(JsonDocument& doc, JsonObject data) {
    doc["status"] = "success";
    doc["result"] = "restarting";
    doc["message"] = "Device will restart in 1ms";

    // Schedule restart in 1ms
    scheduledRestartTime = millis() + 1;
    restartScheduled = true;

    Serial.println("[RESTART] Scheduled in 1ms");
}

/**
 * @brief OTA start command handler.
 *
 * Puts the device into OTA mode and returns timeout information.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_ota_start(JsonDocument& doc, JsonObject data) {
    enterOTAMode();
    doc["status"] = "success";
    doc["result"] = "ota_ready";
    doc["timeout"] = 30000;
}

/**
 * @brief Open setup command handler.
 *
 * Starts AP mode for configuration and returns SSID/IP info.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_open_setup(JsonDocument& doc, JsonObject data) {
    startAP();
    doc["status"] = "success";
    doc["result"] = "ap_started";
    doc["ssid"] = CONFIG_AP_SSID;
    doc["ip"] = "192.168.4.1";
}

/**
 * @brief Web control command handler.
 *
 * Enables/disables web server or returns its status based on action.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data containing "action" field.
 */
void CommandManager::cmd_web_control(JsonDocument& doc, JsonObject data) {
    const char* action = data["action"];
    if (!action) {
        doc["status"] = "error";
        doc["error"] = "ACTION_REQUIRED";
        return;
    }

    if (strcmp(action, "status") == 0) {
        doc["status"] = "success";
        doc["web_enabled"] = webServerEnabled;

    } else if (strcmp(action, "enable") == 0) {
        webServerEnabled = true;
        cfg.web_server_enabled = 1;
        saveConfig();
        doc["status"] = "success";
        doc["result"] = "web_enabled";

    } else if (strcmp(action, "disable") == 0) {
        webServerEnabled = false;
        cfg.web_server_enabled = 0;
        saveConfig();
        doc["status"] = "success";
        doc["result"] = "web_disabled";

    } else {
        doc["status"] = "error";
        doc["error"] = "INVALID_ACTION";
    }
}

/**
 * @brief Cloud control command handler.
 *
 * Enables/disables cloud mode or returns its status based on action.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data containing "action" field.
 */
void CommandManager::cmd_cloud_control(JsonDocument& doc, JsonObject data) {
    const char* action = data["action"];
    if (!action) {
        doc["status"] = "error";
        doc["error"] = "ACTION_REQUIRED";
        return;
    }

    if (strcmp(action, "status") == 0) {
        doc["status"] = "success";
        doc["cloud_enabled"] = isCloudEnabled();
        doc["cloud_status"] = getCloudStatus();

    } else if (strcmp(action, "enable") == 0) {
        enableCloud();
        doc["status"] = "success";
        doc["result"] = "cloud_enabled";
        doc["cloud_status"] = getCloudStatus();

    } else if (strcmp(action, "disable") == 0) {
        disableCloud();
        doc["status"] = "success";
        doc["result"] = "cloud_disabled";

    } else {
        doc["status"] = "error";
        doc["error"] = "INVALID_ACTION";
    }
}

/**
 * @brief Crypto info command handler.
 *
 * Returns information about the cryptographic module and request counter.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_crypto_info(JsonDocument& doc, JsonObject data) {
    doc["status"] = "success";
    doc["enabled"] = crypto.isEnabled();
    doc["requests"] = crypto.getRequestCount();
    doc["limit"] = crypto.getRequestLimit();
    doc["key_info"] = crypto.getKeyInfo();
}

/**
 * @brief Counter info command handler.
 *
 * Returns current request counter value and limit.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_counter_info(JsonDocument& doc, JsonObject data) {
    doc["status"] = "success";
    doc["requests"] = crypto.getRequestCount();
    doc["limit"] = crypto.getRequestLimit();
}

/**
 * @brief Reset counter command handler.
 *
 * Resets the request counter to zero and returns confirmation.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_reset_counter(JsonDocument& doc, JsonObject data) {
    crypto.resetRequestCounter();
    doc["status"] = "success";
    doc["result"] = "counter_reset";
}

/**
 * @brief Update token command handler.
 *
 * Generates a new device_token, saves it to config, and schedules restart.
 *
 * @param doc JsonDocument to store the response.
 * @param data Command data (unused).
 */
void CommandManager::cmd_update_token(JsonDocument& doc, JsonObject data) {
    // Generate new token
    String newToken = crypto.generateToken();

    Serial.println("[TOKEN] Generating new token...");

    // Save to configuration
    strncpy(cfg.device_token, newToken.c_str(), sizeof(cfg.device_token) - 1);
    cfg.device_token[sizeof(cfg.device_token) - 1] = '\0';

    // Save configuration
    saveConfig();

    // Reset request counter on token change
    crypto.resetRequestCounter();

    Serial.println("[TOKEN] Configuration saved successfully");

    doc["status"] = "success";
    doc["result"] = "token_updated";
    doc["new_token"] = newToken;
    doc["message"] = "Token updated. Device will restart in 1ms.";

    // Schedule restart in 1ms
    scheduledRestartTime = millis() + 1;
    restartScheduled = true;

    Serial.println("[TOKEN] Restart scheduled in 1ms");
}

/**
 * @brief Handle scheduled restart.
 *
 * Checks if a scheduled restart needs to be executed and performs it.
 * Called in the main loop().
 */
void CommandManager::handleScheduledRestart() {
    if (restartScheduled && millis() >= scheduledRestartTime) {
        Serial.println("[SCHEDULED] Executing restart...");
        delay(100);
        ESP.restart();
    }
}

/**
 * @brief Execute command by routing string command to appropriate handler.
 *
 * Routes the command string to the corresponding handler based on prefix.
 *
 * @param command The command string to execute.
 * @param data Command data as JsonObject.
 * @return JsonDocument containing the response or error.
 */
JsonDocument CommandManager::executeCommand(const String& command, JsonObject data) {
    JsonDocument doc;
    const char* cmd = command.c_str();

    Serial.printf("[CMD] Executing: %s\n", cmd);

    switch (cmd[0]) {
        case 'p':
            if (strcmp_P(cmd, PSTR("ping")) == 0) { cmd_ping(doc, data); return doc; }
            break;
        case 'w':
            if (strcmp_P(cmd, PSTR("wake")) == 0) { cmd_wake(doc, data); return doc; }
            if (strcmp_P(cmd, PSTR("web_control")) == 0) { cmd_web_control(doc, data); return doc; }
            break;
        case 'i':
            if (strcmp_P(cmd, PSTR("info")) == 0) { cmd_info(doc, data); return doc; }
            break;
        case 'r':
            if (strcmp_P(cmd, PSTR("restart")) == 0) { cmd_restart(doc, data); return doc; }
            if (strcmp_P(cmd, PSTR("reset_counter")) == 0) { cmd_reset_counter(doc, data); return doc; }
            break;
        case 'o':
            if (strcmp_P(cmd, PSTR("ota_start")) == 0) { cmd_ota_start(doc, data); return doc; }
            if (strcmp_P(cmd, PSTR("open_setup")) == 0) { cmd_open_setup(doc, data); return doc; }
            break;
        case 'c':
            if (strcmp_P(cmd, PSTR("crypto_info")) == 0) { cmd_crypto_info(doc, data); return doc; }
            if (strcmp_P(cmd, PSTR("counter_info")) == 0) { cmd_counter_info(doc, data); return doc; }
            if (strcmp_P(cmd, PSTR("cloud_control")) == 0) { cmd_cloud_control(doc, data); return doc; }
            break;
        case 'u':
            if (strcmp_P(cmd, PSTR("update_token")) == 0) {
                Serial.println("[CMD] Found update_token command!");
                cmd_update_token(doc, data);
                return doc;
            }
            break;
    }

    Serial.printf("[CMD] UNKNOWN COMMAND: %s\n", cmd);
    doc["status"] = "error";
    doc["error"] = "UNKNOWN_COMMAND";
    doc["command"] = command;
    return doc;
}
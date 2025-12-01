/**
 * @file command.h
 * @brief Command execution manager for WakeLink firmware.
 * 
 * Implements all device commands that can be executed remotely
 * via TCP, HTTP, or WSS transports. Commands are routed by name
 * to their respective handlers.
 * 
 * Supported Commands:
 * - ping: Connection test, returns "pong"
 * - wake: Send Wake-on-LAN packet to specified MAC
 * - info: Return device information (IP, RSSI, memory, etc.)
 * - restart: Schedule device restart
 * - ota_start: Enable OTA update mode for 30 seconds
 * - open_setup: Start AP mode for configuration
 * - web_control: Enable/disable/status web server
 * - cloud_control: Enable/disable/status cloud WSS connection
 * - crypto_info: Get encryption status and counters
 * - counter_info: Get request counter details
 * - reset_counter: Reset request counter
 * - update_token: Generate new device token
 * 
 * Error Handling:
 * - Unknown commands return UNKNOWN_COMMAND error
 * - Missing parameters return appropriate error messages
 * 
 * @author deadboizxc
 * @version 1.0
 */

#ifndef COMMAND_H
#define COMMAND_H

#include <ArduinoJson.h>

/**
 * @brief Command execution manager class.
 * 
 * Static class that routes command strings to handler functions.
 * Each handler populates a JsonDocument with the result.
 */
class CommandManager {
private:
    static unsigned long scheduledRestartTime;  ///< Time when restart is scheduled
    static bool restartScheduled;               ///< Flag indicating pending restart
    static String newTokenForRestart;           ///< New token to apply after restart

public:
    /**
     * @brief Execute a command by name.
     * 
     * Routes the command string to the appropriate handler.
     * 
     * @param command Command name string (e.g., "ping", "wake").
     * @param data Command parameters as JsonObject.
     * @return JsonDocument with command result or error.
     */
    static JsonDocument executeCommand(const String& command, JsonObject data);

    /**
     * @brief Handle scheduled restart operation.
     * 
     * Checks if a restart is scheduled and executes it.
     * Must be called from loop() for deferred restart to work.
     */
    static void handleScheduledRestart();

    // =============================
    // Command Handlers
    // =============================

    /**
     * @brief Ping command - connection test.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_ping(JsonDocument& doc, JsonObject data);

    /**
     * @brief Wake command - send Wake-on-LAN packet.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (requires "mac" field).
     */
    static void cmd_wake(JsonDocument& doc, JsonObject data);

    /**
     * @brief Info command - get device information.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_info(JsonDocument& doc, JsonObject data);

    /**
     * @brief Restart command - schedule device restart.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_restart(JsonDocument& doc, JsonObject data);

    /**
     * @brief OTA start command - enable OTA update mode.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_ota_start(JsonDocument& doc, JsonObject data);

    /**
     * @brief Open setup command - start AP mode.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_open_setup(JsonDocument& doc, JsonObject data);

    /**
     * @brief Web control command - manage web server.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (requires "action": enable/disable/status).
     */
    static void cmd_web_control(JsonDocument& doc, JsonObject data);

    /**
     * @brief Cloud control command - manage cloud WSS connection.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (requires "action": enable/disable/status).
     */
    static void cmd_cloud_control(JsonDocument& doc, JsonObject data);

    /**
     * @brief Crypto info command - get encryption status.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_crypto_info(JsonDocument& doc, JsonObject data);

    /**
     * @brief Counter info command - get request counter details.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_counter_info(JsonDocument& doc, JsonObject data);

    /**
     * @brief Reset counter command - reset request counter.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_reset_counter(JsonDocument& doc, JsonObject data);

    /**
     * @brief Update token command - generate new device token.
     * @param doc Output JsonDocument for result.
     * @param data Input parameters (unused).
     */
    static void cmd_update_token(JsonDocument& doc, JsonObject data);
};

#endif // COMMAND_H
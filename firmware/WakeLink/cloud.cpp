/**
 * @file cloud.cpp
 * @brief Cloud communication module for WakeLink firmware.
 * 
 * Unified WSS client implementation. Handles WebSocket connection,
 * packet encryption/decryption, and command routing to/from cloud relay.
 * 
 * Protocol v1.0:
 * - Outer JSON: {device_id, payload, signature, version}
 * - Inner encrypted: {command, data, request_id, timestamp}
 * - Hex payload: [2B len][ciphertext][16B nonce]
 * 
 * Authentication:
 * - After connecting, firmware sends auth message:
 *   {"type": "auth", "token": "<api_token>"}
 * - Server responds with welcome message on success or error
 */

#include "cloud.h"
#include "command.h"
#include "packet.h"
#include "platform.h"

extern PacketManager packetManager;
extern String DEVICE_TOKEN;
extern String DEVICE_ID;

// ============================================================================
// WebSocket Client Instance
// ============================================================================

/// WebSocket client instance
static WebSocketsClient _ws_client;

/// Cloud enabled flag
static bool _cloud_enabled = false;

/// WSS connected flag
static bool _ws_connected = false;

/// Auth sent flag (to send auth message only once per connection)
static bool _auth_sent = false;

/// Last WSS state (for logging changes)
static bool _last_ws_connected = false;

/// Parsed URL components
static String _host;
static uint16_t _port = 443;
static String _path;
static bool _use_ssl = true;
static String _api_token;

// ============================================================================
// Forward Declarations
// ============================================================================

static bool _parseUrl(const String& url);
static void _onWsEvent(WStype_t type, uint8_t* payload, size_t length);
static void _processPacket(const String& packet_json);
static void _sendAuthMessage();

// ============================================================================
// Public API
// ============================================================================

void initCloud() {
    String cloud_url = String(cfg.cloud_url);
    
    if (cloud_url.length() == 0) {
        Serial.println("[CLOUD] No URL configured");
        return;
    }
    
    // Convert HTTP to WS scheme
    if (cloud_url.startsWith("https://")) {
        cloud_url.replace("https://", "wss://");
    } else if (cloud_url.startsWith("http://")) {
        cloud_url.replace("http://", "ws://");
    } else if (!cloud_url.startsWith("wss://") && !cloud_url.startsWith("ws://")) {
        cloud_url = "wss://" + cloud_url;
    }
    
    if (!_parseUrl(cloud_url)) {
        Serial.printf("[CLOUD] Invalid URL: %s\n", cloud_url.c_str());
        return;
    }
    
    _api_token = String(cfg.cloud_api_token);
    
    // Build endpoint: /ws/{device_id} (no token in URL for security)
    if (_path.isEmpty() || _path == "/") {
        _path = "/ws/" + DEVICE_ID;
    } else if (_path.indexOf(DEVICE_ID) == -1) {
        if (!_path.endsWith("/")) _path += "/";
        _path += DEVICE_ID;
    }
    
    // Token will be sent in JSON auth message after connection
    
    Serial.printf("[CLOUD] Connecting: %s:%d%s (SSL: %s)\n",
                  _host.c_str(), _port, _path.c_str(),
                  _use_ssl ? "yes" : "no");
    
    // Configure WebSocket
    if (_use_ssl) {
        _ws_client.beginSSL(_host, _port, _path);
        // Heartbeat: 25s interval, 10s timeout, 3 retries
        // More tolerant for Cloudflare/slow networks
        _ws_client.enableHeartbeat(25000, 10000, 3);
    } else {
        _ws_client.begin(_host, _port, _path);
        _ws_client.enableHeartbeat(25000, 10000, 3);
    }
    
    _ws_client.onEvent(_onWsEvent);
    
    // Backup headers for backwards compatibility with older servers
    // Primary auth is via JSON message sent after connection
    if (_api_token.length() > 0) {
        String headers = "X-API-Token: " + _api_token + "\r\n";
        headers += "X-Device-ID: " + DEVICE_ID;
        _ws_client.setExtraHeaders(headers.c_str());
    }
    
    _ws_client.setReconnectInterval(5000);
    
    _cloud_enabled = true;
    _auth_sent = false;  // Reset auth flag
    Serial.println("[CLOUD] Initialized");
}

void handleCloud() {
    if (!_cloud_enabled) return;
    
    // Skip if WiFi down
    if (WiFi.status() != WL_CONNECTED) {
        if (_ws_connected) {
            Serial.println("[CLOUD] WiFi lost");
            _ws_connected = false;
        }
        return;
    }
    
    _ws_client.loop();
    
    // Log state changes
    if (_ws_connected != _last_ws_connected) {
        Serial.printf("[CLOUD] %s\n", _ws_connected ? "Connected" : "Disconnected");
        _last_ws_connected = _ws_connected;
    }
}

void pushCloud(const String& command, const JsonObject& data) {
    if (!_cloud_enabled || !_ws_connected) return;
    
    String packet = packetManager.createCommandPacket(command, data);
    
    if (_ws_client.sendTXT(packet)) {
        Serial.printf("[CLOUD] TX: %s (%d bytes)\n", command.c_str(), packet.length());
    } else {
        Serial.println("[CLOUD] TX failed");
    }
}

void sendCloudResponse(const String& response_packet) {
    if (!_cloud_enabled || !_ws_connected) {
        Serial.println("[CLOUD] Cannot send - not connected");
        return;
    }
    
    String packet = response_packet;  // sendTXT needs non-const
    if (_ws_client.sendTXT(packet)) {
        Serial.println("[CLOUD] Response sent");
    } else {
        Serial.println("[CLOUD] Response failed");
    }
}

bool isCloudConnected() {
    return _cloud_enabled && _ws_connected;
}

String getCloudStatus() {
    if (!_cloud_enabled) return "disabled";
    return _ws_connected ? "connected" : "disconnected";
}

// ============================================================================
// Internal Functions
// ============================================================================

/**
 * @brief Parse WebSocket URL into components.
 */
static bool _parseUrl(const String& url) {
    if (url.startsWith("wss://")) {
        _use_ssl = true;
        _port = 443;
    } else if (url.startsWith("ws://")) {
        _use_ssl = false;
        _port = 80;
    } else {
        return false;
    }
    
    int scheme_end = url.indexOf("://") + 3;
    String remainder = url.substring(scheme_end);
    
    int path_start = remainder.indexOf('/');
    String host_port;
    
    if (path_start != -1) {
        host_port = remainder.substring(0, path_start);
        _path = remainder.substring(path_start);
    } else {
        host_port = remainder;
        _path = "/";
    }
    
    int port_sep = host_port.indexOf(':');
    if (port_sep != -1) {
        _host = host_port.substring(0, port_sep);
        _port = host_port.substring(port_sep + 1).toInt();
    } else {
        _host = host_port;
    }
    
    return _host.length() > 0;
}

/**
 * @brief WebSocket event handler.
 */
static void _onWsEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            _ws_connected = false;
            _auth_sent = false;  // Reset auth flag on disconnect
            break;
            
        case WStype_CONNECTED:
            _ws_connected = true;
            Serial.printf("[CLOUD] Connected to %s\n", (char*)payload);
            // Send auth message immediately after connection
            _sendAuthMessage();
            break;
            
        case WStype_TEXT: {
            String json;
            json.reserve(length + 1);
            for (size_t i = 0; i < length; i++) {
                json += (char)payload[i];
            }
            
            // Skip server status messages (welcome, auth response, etc.)
            if (json.indexOf("\"status\"") != -1 && json.indexOf("\"payload\"") == -1) {
                Serial.printf("[CLOUD] Server: %s\n", json.c_str());
                
                // Check for auth error
                if (json.indexOf("\"error\"") != -1) {
                    Serial.println("[CLOUD] Auth failed, disconnecting");
                    _ws_client.disconnect();
                }
                break;
            }
            
            Serial.printf("[CLOUD] RX: %u bytes\n", length);
            _processPacket(json);
            break;
        }
            
        case WStype_PING:
            Serial.println("[CLOUD] Ping");
            break;
            
        case WStype_PONG:
            Serial.println("[CLOUD] Pong");
            break;
            
        case WStype_ERROR:
            Serial.printf("[CLOUD] Error: %s\n", payload ? (char*)payload : "unknown");
            break;
            
        default:
            break;
    }
}

/**
 * @brief Send authentication message to server.
 * 
 * Sends JSON: {"type": "auth", "token": "<api_token>"}
 */
static void _sendAuthMessage() {
    if (_auth_sent || _api_token.length() == 0) {
        return;
    }
    
    JsonDocument auth;
    auth["type"] = "auth";
    auth["token"] = _api_token;
    
    String authJson;
    serializeJson(auth, authJson);
    
    if (_ws_client.sendTXT(authJson)) {
        Serial.println("[CLOUD] Auth message sent");
        _auth_sent = true;
    } else {
        Serial.println("[CLOUD] Auth message failed");
    }
}

/**
 * @brief Enable cloud mode and initialize connection.
 */
void enableCloud() {
    if (_cloud_enabled) {
        Serial.println("[CLOUD] Already enabled");
        return;
    }
    
    cfg.cloud_enabled = 1;
    saveConfig();
    
    Serial.println("[CLOUD] Enabling...");
    initCloud();
}

/**
 * @brief Disable cloud mode and disconnect.
 */
void disableCloud() {
    if (!_cloud_enabled) {
        Serial.println("[CLOUD] Already disabled");
        return;
    }
    
    _cloud_enabled = false;
    _ws_connected = false;
    _auth_sent = false;  // Reset auth flag
    _ws_client.disconnect();
    
    cfg.cloud_enabled = 0;
    saveConfig();
    
    Serial.println("[CLOUD] Disabled");
}

/**
 * @brief Check if cloud mode is enabled.
 */
bool isCloudEnabled() {
    return cfg.cloud_enabled == 1;
}

/**
 * @brief Process incoming encrypted packet.
 */
static void _processPacket(const String& packet_json) {
    JsonDocument incoming = packetManager.processIncomingPacket(packet_json);
    
    if (incoming["status"] != "success") {
        const char* error = incoming["error"] | "DECRYPT_FAILED";
        Serial.printf("[CLOUD] Error: %s\n", error);
        
        JsonDocument err;
        err["status"] = "error";
        err["error"] = error;
        err["request_id"] = incoming["request_id"];
        
        sendCloudResponse(packetManager.createResponsePacket(err));
        return;
    }
    
    const char* command = incoming["command"];
    JsonObject data = incoming["data"].as<JsonObject>();
    
    Serial.printf("[CLOUD] Command: %s\n", command);
    
    JsonDocument result = CommandManager::executeCommand(String(command), data);
    result["request_id"] = incoming["request_id"];
    
    sendCloudResponse(packetManager.createResponsePacket(result));
}

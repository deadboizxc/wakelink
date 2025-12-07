#include "platform.h"
#include "config.h"
#include "wifi_manager.h"
#include "web_server.h"
#include "tcp_handler.h"
#include "udp_handler.h"
#include "ota_manager.h"
#include "packet.h"
#include "CryptoManager.h"
#include "cloud.h"
#include "command.h"

/**
 * @file WakeLink.ino
 * @brief Main entry point for WakeLink firmware.
 * 
 * Orchestrates all subsystems: WiFi, TCP server, cloud client (WSS/HTTP),
 * web server, OTA updates, and hardware reset functionality.
 * 
 * Protocol v1.0 with three equal transports:
 * - TCP port 99 (local network)
 * - HTTP push/pull (cloud polling)
 * - WSS (cloud real-time)
 */

/// Crypto manager instance for encryption/decryption operations
CryptoManager crypto;

/// Packet manager using crypto for signing/encryption
PacketManager packetManager(crypto);

/// TCP handler for local network communication
TCPHandler tcpHandler(TCP_PORT, &packetManager);

/// Timer for main loop operations
static unsigned long lastLoopTime = 0;

/// Reset button state tracking
static bool resetButtonPressed = false;

/// Reset button press start time
static unsigned long resetButtonPressTime = 0;

/// Reset operation in progress flag
static bool resetInProgress = false;

// Forward declarations
void performFullReset();
void handleResetButton();

/**
 * @brief Arduino setup function.
 * 
 * Initializes all subsystems in order:
 * 1. Serial port and GPIO
 * 2. EEPROM and configuration
 * 3. Crypto manager
 * 4. WiFi connection
 * 5. Web server, UDP, OTA, TCP
 * 6. Cloud client (WSS or HTTP)
 */
void setup() {
    Serial.begin(115200);
    while (!Serial) delay(10);

    Serial.println(F("\nWakeLink v1.0 - Universal Protocol"));
    Serial.printf("Platform: %s\n",
    #ifdef ESP8266
        "ESP8266"
    #else
        "ESP32"
    #endif
    );
    Serial.println(F("=== START ==="));

    // Initialize hardware pins
    pinMode(STATUS_LED, OUTPUT);
    digitalWrite(STATUS_LED, HIGH);
    pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);

    // Load configuration from EEPROM
    EEPROM.begin(EEPROM_SIZE);
    loadConfig();

    // Initialize crypto manager
    if (!crypto.begin()) {
        Serial.println("[CRYPTO] Initialization failed!");
    } else {
        Serial.println("[CRYPTO] Initialized successfully");
    }

    // First boot: generate device ID and token
    if (!cfg.initialized) {
        Serial.println(F("[CONFIG] First boot detected"));

        String id = "WL" + getChipId();
        id.toUpperCase();
        strncpy(cfg.device_id, id.c_str(), sizeof(cfg.device_id) - 1);

        String token = crypto.generateToken();
        strncpy(cfg.device_token, token.c_str(), sizeof(cfg.device_token) - 1);

        cfg.initialized = 1;
        cfg.cloud_enabled = 0;
        cfg.wifi_configured = 0;
        cfg.web_server_enabled = 1;
        saveConfig();

        Serial.printf("[CONFIG] Device ID: %s\n", cfg.device_id);
    }

    // Set global variables for packet manager
    DEVICE_ID = cfg.device_id;
    DEVICE_TOKEN = cfg.device_token;
    webServerEnabled = cfg.web_server_enabled;

    Serial.printf("[SYSTEM] Chip ID: %s | Heap: %lu bytes\n",
                  getChipId().c_str(),
                  (unsigned long)ESP.getFreeHeap());

    // Initialize subsystems
    setupSecureClient(clientSecure);
    initWiFi();
    initWebServer();
    initUDP();
    initOTA();
    tcpHandler.begin();

    // Initialize cloud client (handles both WSS and HTTP modes)
    // Only initialize if cloud is enabled AND we're connected to WiFi (not in AP mode)
    if (cfg.cloud_enabled && !inAPMode) {
        initCloud();
    } else if (cfg.cloud_enabled && inAPMode) {
        Serial.println(F("[CLOUD] Skipped - device in AP mode (no internet)"));
    }

    Serial.println(F("=== SETUP COMPLETE ==="));

    // Startup LED indication
    for (int i = 0; i < 2; i++) {
        digitalWrite(STATUS_LED, LOW);
        delay(80);
        digitalWrite(STATUS_LED, HIGH);
        delay(80);
    }
}

/**
 * @brief Arduino main loop function.
 * 
 * Handles all periodic tasks:
 * - Reset button monitoring
 * - WiFi connection maintenance
 * - TCP client handling
 * - Cloud communication (WSS events or HTTP polling)
 * - OTA update checks
 * - Web server requests
 * - Scheduled command restarts
 */
void loop() {
    unsigned long currentMillis = millis();

    // Check reset button first
    handleResetButton();
    if (resetInProgress) {
        return;
    }

    // Handle WiFi connection
    handleWiFi();

    // Handle TCP connections
    tcpHandler.handle();

    // Handle cloud communication (WSS or HTTP) - only if connected to WiFi
    if (cfg.cloud_enabled && !inAPMode) {
        handleCloud();
    }

    // Handle OTA updates
    handleOTA();

    // Handle web server requests
    if (webServerEnabled) {
        server.handleClient();
    }

    // Check for scheduled restarts
    CommandManager::handleScheduledRestart();

    // High-frequency loop tasks
    if (currentMillis - lastLoopTime >= 1) {
        lastLoopTime = currentMillis;

        // OTA mode timeout (30 seconds)
        if (otaMode && currentMillis - otaStartTime > 30000) {
            otaMode = false;
            Serial.println("[OTA] Mode timed out");
        }
    }
}

/**
 * @brief Perform full factory reset.
 * 
 * Erases all configuration, clears WiFi credentials, resets
 * the crypto request counter, and reboots the device.
 * 
 * @warning This operation is destructive and cannot be undone.
 */
void performFullReset() {
    Serial.println(F("\nFACTORY RESET IN PROGRESS"));

    for (int i = 0; i < 10; i++) {
        digitalWrite(STATUS_LED, LOW);
        delay(100);
        digitalWrite(STATUS_LED, HIGH);
        delay(100);
    }

    Serial.println(F("Erasing configuration..."));
    memset(&cfg, 0, sizeof(cfg));
    cfg.initialized = 0;

    // Reset request counter in cryptographic module
    crypto.resetRequestCounter();

    saveConfig();

    Serial.println(F("Clearing WiFi credentials..."));
    WiFi.disconnect(true);
    delay(1000);
    WiFi.mode(WIFI_OFF);

    #ifdef ESP8266
        ESP.eraseConfig();
    #else
        WiFi.persistent(true);
        WiFi.begin("0", "0");
        delay(1000);
        WiFi.disconnect(true);
        delay(1000);
        WiFi.persistent(false);
    #endif

    Serial.println(F("Reset complete. Rebooting..."));
    digitalWrite(STATUS_LED, LOW);
    delay(1000);

    ESP.restart();
}

/**
 * @brief Handle hardware reset button.
 * 
 * Monitors the reset button state and triggers factory reset
 * when held for 5+ seconds. Provides LED feedback during the hold.
 * 
 * - Short press (<5s): Reset cancelled
 * - Long press (>=5s): Factory reset initiated
 */
void handleResetButton() {
    int buttonState = digitalRead(RESET_BUTTON_PIN);

    if (buttonState == LOW && !resetButtonPressed && !resetInProgress) {
        resetButtonPressed = true;
        resetButtonPressTime = millis();
        Serial.println("Reset button pressed...");
        digitalWrite(STATUS_LED, LOW);
        delay(100);
        digitalWrite(STATUS_LED, HIGH);
    }

    if (buttonState == HIGH && resetButtonPressed && !resetInProgress) {
        unsigned long pressDuration = millis() - resetButtonPressTime;

        if (pressDuration >= 5000) {
            Serial.println("Reset confirmed, performing full reset...");
            resetInProgress = true;
            performFullReset();
        } else {
            Serial.println("Reset cancelled (too short)");
        }
        resetButtonPressed = false;
    }

    if (resetButtonPressed && !resetInProgress) {
        unsigned long currentPressTime = millis() - resetButtonPressTime;

        if (currentPressTime > 4000) {
            if (currentPressTime % 200 < 100) {
                digitalWrite(STATUS_LED, LOW);
            } else {
                digitalWrite(STATUS_LED, HIGH);
            }
        } else {
            if (currentPressTime % 1000 < 500) {
                digitalWrite(STATUS_LED, LOW);
            } else {
                digitalWrite(STATUS_LED, HIGH);
            }
        }
    }
}
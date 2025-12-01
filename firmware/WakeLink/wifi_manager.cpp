#include "wifi_manager.h"
#include "platform.h"

/**
 * @brief Initialize WiFi connection.
 *
 * Attempts to connect to saved network if cfg.wifi_configured and SSID are set.
 * Blocks until connected or max retries exhausted.
 * Falls back to Access Point via startAP() on failure or missing configuration.
 */
void initWiFi() {
    if (cfg.wifi_configured && strlen(cfg.wifi_ssid)) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(cfg.wifi_ssid, cfg.wifi_pass);
        Serial.print(F("Connecting to WiFi '"));
        Serial.print(cfg.wifi_ssid);
        Serial.println(F("'"));

        uint8_t tries = 0;
        while (WiFi.status() != WL_CONNECTED && tries < 40) {
            delay(500);
            Serial.print('.');
            blink(1, 50);
            ++tries;
        }
        Serial.println();

        if (WiFi.status() == WL_CONNECTED) {
            Serial.println(F("WiFi Connected"));
            Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
            inAPMode = false;
            return;
        } else {
            Serial.println(F("WiFi connection failed"));
        }
    } else {
        Serial.println(F("WiFi not configured"));
    }

    Serial.println(F("Starting Access Point"));
    startAP();
}

/**
 * @brief Handle WiFi state in main loop.
 *
 * In AP mode: monitors configuration portal timeout and triggers reboot.
 * In STA mode: periodically checks connection and attempts reconnection on disconnect.
 */
void handleWiFi() {
    if (inAPMode) {
        if (millis() - apModeStartTime > CONFIG_PORTAL_TIMEOUT) {
            Serial.println(F("AP timeout - reboot"));
            ESP.restart();
        }
    } else {
        static unsigned long lastCheck = 0;
        if (millis() - lastCheck > 30000) {
            lastCheck = millis();

            if (WiFi.status() != WL_CONNECTED) {
                Serial.println(F("WiFi disconnected, reconnecting..."));
                WiFi.reconnect();
                delay(1000);

                unsigned long reconnectStart = millis();
                while (WiFi.status() != WL_CONNECTED && millis() - reconnectStart < 10000) {
                    delay(500);
                }

                if (WiFi.status() != WL_CONNECTED) {
                    Serial.println(F("Reconnect failed, starting AP"));
                    startAP();
                } else {
                    Serial.println(F("WiFi reconnected"));
                }
            }
        }
    }
}

/**
 * @brief Start Access Point mode.
 *
 * Switches module to AP mode, sets SSID/password, updates state flags, and prints hints.
 * Used for device configuration via web interface.
 */
void startAP() {
    inAPMode = true;
    apModeStartTime = millis();

    WiFi.disconnect();
    delay(100);
    WiFi.mode(WIFI_AP);

    WiFi.softAP(CONFIG_AP_SSID, CONFIG_AP_PASS);
    delay(100);

    Serial.printf("===========================\n"
                 "SSID: %s\n"
                 "Password: %s\n"
                 "IP: %s\n"
                 "Connect: http://192.168.4.1\n"
                 "===========================\n", 
                 CONFIG_AP_SSID, CONFIG_AP_PASS, 
                 WiFi.softAPIP().toString().c_str());

    blink(10, 100);
}

/**
 * @brief Check if device is in Access Point mode.
 *
 * @return true if in AP mode (used by web interface and control logic).
 */
bool isInAPMode() {
    return inAPMode;
}
#include "config.h"
#include "CryptoManager.h"
#include "platform.h"

extern CryptoManager crypto;

DeviceConfig cfg;
WiFiUDP udp;
WiFiServer tcpServer(TCP_PORT);
WiFiClientSecure clientSecure;
WebServerType server(80);
unsigned long lastCloudPoll = 0;
bool inAPMode = false;
unsigned long apModeStartTime = 0;
bool otaMode = false;
unsigned long otaStartTime = 0;
String DEVICE_TOKEN = "";
String DEVICE_ID = "";
bool webServerEnabled = true;

/**
 * @brief Load configuration from EEPROM.
 *
 * Reads cfg structure from EEPROM and checks validity marker.
 * If no valid save exists, initializes cfg with defaults and generates device_id/device_token.
 */
void loadConfig() {
    EEPROM.begin(EEPROM_SIZE);

    uint8_t *ptr = (uint8_t*)&cfg;
    for (size_t i = 0; i < sizeof(cfg); i++) {
        ptr[i] = EEPROM.read(i);
    }

    bool configValid = (EEPROM.read(sizeof(cfg)) == 0xAA &&
                       EEPROM.read(sizeof(cfg) + 1) == 0xBB);

    EEPROM.end();

    if (!configValid) {
        Serial.println(F("No valid config, using defaults"));
        memset(&cfg, 0, sizeof(cfg));
        cfg.initialized = 0;
        cfg.wifi_configured = 0;
        cfg.cloud_enabled = 0;
        cfg.web_server_enabled = 1;

        if (strlen(cfg.device_id) == 0) {
            String id = "WL" + getChipId();
            id.toUpperCase();
            strncpy(cfg.device_id, id.c_str(), sizeof(cfg.device_id) - 1);
        }

        if (strlen(cfg.device_token) == 0) {
            String token = crypto.generateToken();
            token.toCharArray(cfg.device_token, sizeof(cfg.device_token));
        }

        saveConfig();
    } else {
        Serial.println(F("Config loaded from EEPROM"));
    }

    DEVICE_ID = String(cfg.device_id);
    DEVICE_TOKEN = String(cfg.device_token);
}

/**
 * @brief Save configuration to EEPROM.
 *
 * Serializes cfg to EEPROM and sets validity marker.
 *
 * @return true on successful commit, false on failure.
 */
bool saveConfig() {
    Serial.println(F("Saving config to EEPROM..."));

    EEPROM.begin(EEPROM_SIZE);

    uint8_t *ptr = (uint8_t*)&cfg;
    for (size_t i = 0; i < sizeof(cfg); i++) {
        EEPROM.write(i, ptr[i]);
    }

    EEPROM.write(sizeof(cfg), 0xAA);
    EEPROM.write(sizeof(cfg) + 1, 0xBB);

    bool success = EEPROM.commit();
    EEPROM.end();

    Serial.printf("Config save %s\n", success ? "successful" : "failed");
    return success;
}

/**
 * @brief Blink STATUS_LED.
 *
 * Utility for blinking STATUS_LED specified number of times with given delay.
 *
 * @param times Number of blinks.
 * @param ms Delay in milliseconds.
 */
void blink(int times, int ms) {
    for (int i = 0; i < times; ++i) {
        digitalWrite(STATUS_LED, LOW);
        delay(ms);
        digitalWrite(STATUS_LED, HIGH);
        delay(ms);
    }
}

/**
 * @brief Convert hex character to integer value.
 *
 * @param c Hex character ('0'-'9', 'a'-'f', 'A'-'F').
 * @return Integer value (0-15).
 */
uint8_t hex_char_to_int(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return 0;
}
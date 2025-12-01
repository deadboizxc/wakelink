#include "ota_manager.h"

/**
 * @brief Initialize ArduinoOTA subsystem.
 *
 * Configures hostname, password, and callbacks for update start/end.
 * Registers simple callbacks and starts the OTA subsystem.
 */
void initOTA() {
    ArduinoOTA.setHostname(OTA_HOSTNAME);
    ArduinoOTA.setPassword(OTA_PASSWORD);
    ArduinoOTA.onStart([]() {
        Serial.println(F("OTA start"));
        digitalWrite(STATUS_LED, LOW);
    });
    ArduinoOTA.onEnd([]() {
        Serial.println(F("OTA end"));
        digitalWrite(STATUS_LED, HIGH);
    });
    ArduinoOTA.begin();
    Serial.println(F("OTA OK"));
}

/**
 * @brief Handle incoming OTA traffic.
 *
 * Must be called in loop() to process incoming OTA traffic.
 */
void handleOTA() {
    ArduinoOTA.handle();
}

/**
 * @brief Enter OTA mode.
 *
 * Sets otaMode flag, stops UDP, and blinks LED for indication.
 */
void enterOTAMode() {
    otaMode = true;
    otaStartTime = millis();
    udp.stop();
    Serial.println(F("OTA mode"));
    blink(8, 100);
}
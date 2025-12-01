#include "packet.h"
#include "platform.h"

extern DeviceConfig cfg;
extern String DEVICE_ID;

/**
 * @brief Generate short unique request identifier.
 *
 * Creates simple 8-character ID from limited character set.
 * Used to bind response to request.
 *
 * @return Request ID string.
 */
String PacketManager::generateRequestId() {
    const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    String id = "";
    for (int i = 0; i < 8; ++i) {
        id += chars[random(0, 36)];
    }
    return id;
}

/**
 * @brief Create signed command packet.
 *
 * Assembles internal JSON with command, data, request_id, timestamp.
 * Encrypts internal JSON and forms outer packet via createOuterPacket.
 *
 * @param command Command name.
 * @param data Command data object.
 * @return Serialized signed outer packet.
 */
String PacketManager::createCommandPacket(const String& command, const JsonObject& data) {
    JsonDocument innerDoc;
    innerDoc["command"] = command;
    innerDoc["data"] = data;
    innerDoc["request_id"] = generateRequestId();
    innerDoc["timestamp"] = millis();

    String encryptedPayload = encryptJson(innerDoc);
    return createOuterPacket(encryptedPayload);
}

/**
 * @brief Create outer JSON packet.
 *
 * Forms JSON with device_id, payload, signature, and version fields.
 * Signature is computed via crypto.calculateHMAC for payload.
 *
 * @param encryptedPayload Hex-encoded encrypted payload.
 * @return Serialized outer JSON packet.
 */
String PacketManager::createOuterPacket(const String& encryptedPayload) {
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["payload"] = encryptedPayload;
    doc["signature"] = crypto.calculateHMAC(encryptedPayload);
    doc["version"] = "1.0";

    String out;
    serializeJson(doc, out);
    return out;
}

/**
 * @brief Parse outer JSON packet.
 *
 * Deserializes outer JSON, validates required fields and version.
 * Verifies HMAC signature using crypto.verifyHMAC.
 * Returns JsonDocument with status and encrypted_payload or error.
 *
 * @param packet Raw outer JSON packet.
 * @return JsonDocument with parsing result.
 */
JsonDocument PacketManager::parseOuterPacket(const String& packet) {
    JsonDocument doc, result;

    if (deserializeJson(doc, packet)) {
        result["status"] = "error";
        result["error"] = "JSON_PARSE";
        return result;
    }

    String payload = doc["payload"] | "";
    String sig = doc["signature"] | "";
    String version = doc["version"] | "";

    if (version != "1.0" || payload.isEmpty() || sig.isEmpty()) {
        result["status"] = "error";
        result["error"] = "BAD_PACKET";
        return result;
    }

    if (!crypto.verifyHMAC(payload, sig)) {
        Serial.printf("[SIGN] Expected: %s\n", crypto.calculateHMAC(payload).c_str());
        Serial.printf("[SIGN] Received: %s\n", sig.c_str());
        result["status"] = "error";
        result["error"] = "INVALID_SIGNATURE";
        return result;
    }

    Serial.println("[SIGN] Signature OK");

    result["status"] = "success";
    result["encrypted_payload"] = payload;
    return result;
}

/**
 * @brief Process incoming encrypted packet.
 *
 * Parses outer packet, decrypts internal JSON via crypto.processSecurePacket.
 * Validates internal JSON structure (presence of command field).
 * Returns JsonDocument with status and data/error.
 *
 * @param packetData Raw incoming packet.
 * @return JsonDocument with processing result.
 */
JsonDocument PacketManager::processIncomingPacket(const String& packetData) {
    JsonDocument result;
    
    JsonDocument outerResult = parseOuterPacket(packetData);
    if (outerResult["status"] != "success") {
        return outerResult;
    }
    
    String encryptedPayload = outerResult["encrypted_payload"];
    
    String decrypted = crypto.processSecurePacket(encryptedPayload);
    if (decrypted.startsWith("ERROR:")) {
        result["status"] = "error";
        result["error"] = decrypted;
        return result;
    }
    
    DeserializationError error = deserializeJson(result, decrypted);
    if (error) {
        result["status"] = "error";
        result["error"] = "INVALID_JSON";
        result["raw_error"] = error.c_str();
        return result;
    }
    
    if (result["command"].isNull()) {
        result["status"] = "error";
        result["error"] = "NO_COMMAND";
        return result;
    }
    
    JsonVariant dataVar = result["data"];
    if (dataVar.isNull() || !dataVar.is<JsonObject>()) {
        result["data"].to<JsonObject>();
    }
    
    result["status"] = "success";
    return result;
}

/**
 * @brief Create encrypted response packet.
 *
 * Encrypts JsonDocument result and forms outer signed packet.
 *
 * @param resultData Result data to send.
 * @return Serialized signed outer packet.
 */
String PacketManager::createResponsePacket(const JsonDocument& resultData) {
    String encryptedPayload = encryptJson(resultData);
    return createOuterPacket(encryptedPayload);
}

/**
 * @brief Encrypt JSON document.
 *
 * Serializes json to string and calls crypto.createSecureResponse to get hex packet.
 *
 * @param json JSON document to encrypt.
 * @return Hex-encoded encrypted payload.
 */
String PacketManager::encryptJson(const JsonDocument& json) {
    String plaintext;
    serializeJson(json, plaintext);
    return crypto.createSecureResponse(plaintext);
}
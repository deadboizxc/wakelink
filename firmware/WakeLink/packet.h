/**
 * @file packet.h
 * @brief Protocol v1.0 packet manager for WakeLink firmware.
 * 
 * Handles creation and parsing of encrypted, signed protocol packets.
 * Implements the WakeLink communication protocol used across all transports
 * (TCP, HTTP, WSS).
 * 
 * Packet Structure:
 * - Outer JSON: {device_id, payload, signature, version}
 * - Payload: hex string = [uint16_be length] + [ciphertext] + [16B nonce]
 * - Signature: HMAC-SHA256 of payload hex string only
 * - Inner JSON: {command, data, request_id, timestamp}
 * 
 * Security:
 * - Encryption: ChaCha20 with key derived from device_token
 * - Authentication: HMAC-SHA256 signature over payload
 * - Replay protection: Request counter with EEPROM persistence
 * 
 * @note Compatible with Python client packet.py implementation.
 * 
 * @author deadboizxc
 * @version 1.0
 */

#ifndef PACKET_H
#define PACKET_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "CryptoManager.h"
#include "config.h"

/**
 * @brief Protocol packet manager class.
 * 
 * Provides methods for creating command packets, processing incoming
 * packets, and creating response packets. All operations use the
 * CryptoManager for encryption and signing.
 */
class PacketManager {
private:
    CryptoManager& crypto;  ///< Reference to crypto manager

public:
    /**
     * @brief Construct packet manager with crypto reference.
     * 
     * @param cryptoManager Reference to initialized CryptoManager.
     */
    PacketManager(CryptoManager& cryptoManager) : crypto(cryptoManager) {}

    // =============================
    // Public API Methods
    // =============================

    /**
     * @brief Create a signed, encrypted command packet.
     * 
     * Builds inner JSON with command/data/request_id/timestamp,
     * encrypts it, and wraps in outer JSON with signature.
     * 
     * @param command Command name string.
     * @param data Command parameters as JsonObject.
     * @return Serialized outer packet JSON string.
     */
    String createCommandPacket(const String& command, const JsonObject& data);

    /**
     * @brief Process an incoming encrypted packet.
     * 
     * Parses outer JSON, verifies HMAC signature, decrypts payload,
     * and returns the inner command data.
     * 
     * @param packetData Raw packet JSON string.
     * @return JsonDocument with status and command/data or error.
     */
    JsonDocument processIncomingPacket(const String& packetData);

    /**
     * @brief Create a signed, encrypted response packet.
     * 
     * Encrypts the result data and wraps in outer JSON with signature.
     * 
     * @param resultData Response data as JsonDocument.
     * @return Serialized outer packet JSON string.
     */
    String createResponsePacket(const JsonDocument& resultData);

private:
    /**
     * @brief Generate unique 8-character request ID.
     * 
     * Creates random alphanumeric ID for request/response correlation.
     * 
     * @return Request ID string.
     */
    String generateRequestId();

    /**
     * @brief Encrypt JSON document to hex payload.
     * 
     * Serializes JSON, encrypts with ChaCha20, and returns hex string.
     * 
     * @param json JSON document to encrypt.
     * @return Hex-encoded encrypted payload.
     */
    String encryptJson(const JsonDocument& json);

    /**
     * @brief Create outer JSON packet wrapper.
     * 
     * Adds device_id, payload, signature, and version fields.
     * 
     * @param encryptedPayload Hex-encoded encrypted payload.
     * @return Serialized outer JSON packet.
     */
    String createOuterPacket(const String& encryptedPayload);

    /**
     * @brief Parse and validate outer JSON packet.
     * 
     * Validates structure, version, and HMAC signature.
     * 
     * @param outerPacket Raw outer JSON string.
     * @return JsonDocument with status and encrypted_payload or error.
     */
    JsonDocument parseOuterPacket(const String& outerPacket);
};

#endif // PACKET_H
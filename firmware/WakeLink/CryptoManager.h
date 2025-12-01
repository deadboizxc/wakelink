/**
 * @file CryptoManager.h
 * @brief Cryptographic operations manager for WakeLink firmware.
 * 
 * Implements all cryptographic operations required by protocol v1.0:
 * - ChaCha20 stream cipher for encryption/decryption
 * - SHA256 hash function (software implementation)
 * - HMAC-SHA256 for packet authentication
 * - Request counter for replay protection
 * 
 * Key Derivation:
 * - Both ChaCha20 and HMAC keys are SHA256 of device_token
 * - Nonces are randomly generated per packet
 * 
 * Packet Format (hex payload):
 * - [2 bytes BE length] + [ciphertext] + [16 bytes nonce (first 12 used)]
 * 
 * Request Counter:
 * - Stored in EEPROM at address 386
 * - Incremented on every decrypt operation
 * - Persisted every 10 operations
 * - Limit: 1000 requests before reset required
 * 
 * @note Must call begin() before any crypto operations.
 * 
 * @author deadboizxc
 * @version 1.0
 */

#ifndef CRYPTO_MANAGER_H
#define CRYPTO_MANAGER_H

#include <Arduino.h>
#include "config.h"

// Forward declaration instead of extern
struct DeviceConfig;

/**
 * @brief Cryptographic operations manager class.
 *
 * Provides all crypto primitives needed for WakeLink protocol.
 * Software implementation - no external crypto libraries required.
 */
class CryptoManager {
private:
    // =============================
    // Cryptographic Keys and State
    // =============================
    
    uint8_t chacha_key[32];     ///< ChaCha20 encryption key (SHA256 of device_token)
    uint8_t hmac_key[32];       ///< HMAC key (same derivation as chacha_key)
    uint8_t chacha_nonce[12];   ///< 12-byte nonce for ChaCha20 (from 16-byte packet nonce)
    uint8_t hmac_nonce[32];     ///< 32-byte nonce for HMAC operations
    bool enabled = false;       ///< True if crypto is initialized with valid token
    
    // =============================
    // Request Counter (Replay Protection)
    // =============================
    
    uint32_t requestCounter = 0;        ///< Current request counter value
    const uint32_t requestLimit = 1000; ///< Maximum requests before reset required

    // =============================
    // SHA256 Internal State
    // =============================
    
    uint32_t sha256_state[8];    ///< SHA256 hash state (8x32-bit words)
    uint8_t sha256_buffer[64];   ///< SHA256 input buffer
    uint64_t sha256_bitlen;      ///< Total bits processed
    uint32_t sha256_buffer_len;  ///< Bytes in buffer

    // =============================
    // SHA256 Helper Functions
    // =============================
    
    /** @brief Rotate right operation. */
    uint32_t sha256_rotr(uint32_t x, uint32_t n);
    /** @brief Choice function: (x AND y) XOR (NOT x AND z). */
    uint32_t sha256_ch(uint32_t x, uint32_t y, uint32_t z);
    /** @brief Majority function: (x AND y) XOR (x AND z) XOR (y AND z). */
    uint32_t sha256_maj(uint32_t x, uint32_t y, uint32_t z);
    /** @brief Sigma0 transformation. */
    uint32_t sha256_sigma0(uint32_t x);
    /** @brief Sigma1 transformation. */
    uint32_t sha256_sigma1(uint32_t x);
    /** @brief Gamma0 transformation. */
    uint32_t sha256_gamma0(uint32_t x);
    /** @brief Gamma1 transformation. */
    uint32_t sha256_gamma1(uint32_t x);
    /** @brief Process one 512-bit block. */
    void sha256_transform();
    /** @brief Initialize SHA256 state. */
    void sha256_init();
    /** @brief Update hash with data. */
    void sha256_update(const uint8_t* data, size_t len);
    /** @brief Finalize and output hash. */
    void sha256_final(uint8_t* hash);

    // =============================
    // ChaCha20 Functions
    // =============================
    
    /**
     * @brief Generate one ChaCha20 keystream block.
     * @param key 256-bit encryption key.
     * @param nonce 96-bit nonce.
     * @param counter Block counter.
     * @param output 64-byte output buffer.
     */
    void chacha20_block(const uint8_t key[32], const uint8_t nonce[12], uint32_t counter, uint8_t output[64]);
    
    /**
     * @brief ChaCha20 encrypt/decrypt (symmetric).
     * @param key 256-bit encryption key.
     * @param nonce 96-bit nonce.
     * @param input Input data.
     * @param output Output buffer.
     * @param length Data length.
     */
    void chacha20_encrypt(const uint8_t key[32], const uint8_t nonce[12], const uint8_t* input, uint8_t* output, size_t length);

    // =============================
    // HMAC-SHA256 Functions
    // =============================
    
    /**
     * @brief HMAC-SHA256 with additional nonce.
     */
    void hmac_sha256_with_nonce(const uint8_t* key, size_t key_len, const uint8_t* nonce, size_t nonce_len, const uint8_t* data, size_t data_len, uint8_t* result);
    
    /**
     * @brief Standard HMAC-SHA256.
     */
    void hmac_sha256(const uint8_t* key, size_t key_len, const uint8_t* data, size_t data_len, uint8_t* result);
    
    // =============================
    // EEPROM Persistence
    // =============================
    
    /** @brief Load request counter from EEPROM address 386. */
    void loadRequestCounter();
    /** @brief Save request counter to EEPROM address 386. */
    void saveRequestCounter();

public:
    // =============================
    // Initialization
    // =============================
    
    /**
     * @brief Initialize crypto manager with device token.
     *
     * Derives ChaCha20 and HMAC keys from cfg.device_token using SHA256.
     * Loads request counter from EEPROM.
     *
     * @return true if initialization successful, false if token invalid/empty.
     */
    bool begin();

    // =============================
    // Packet Processing
    // =============================
    
    /**
     * @brief Decrypt and validate incoming encrypted packet.
     *
     * Parses hex payload, extracts nonce, decrypts with ChaCha20,
     * and increments request counter.
     *
     * @param hexPacket Hex-encoded encrypted packet (without outer JSON wrapper).
     * @return Decrypted plaintext JSON, or "ERROR:*" string on failure.
     * 
     * @note Possible errors: LIMIT_EXCEEDED, INVALID_PACKET
     */
    String processSecurePacket(const String& hexPacket);

    /**
     * @brief Encrypt plaintext for transmission.
     *
     * Generates random nonce, encrypts with ChaCha20, and formats
     * as hex packet ready for outer JSON wrapper.
     *
     * @param plaintext Plain text JSON to encrypt.
     * @return Hex-encoded encrypted packet.
     */
    String createSecureResponse(const String& plaintext);

    // =============================
    // Counter Management
    // =============================
    
    /** @brief Increment request counter and persist if needed. */
    void incrementCounter();
    
    /** @brief Check if request limit exceeded. */
    bool isLimitExceeded() const { return requestCounter >= requestLimit; }
    
    /** @brief Check if crypto is enabled (token configured). */
    bool isEnabled() const { return enabled; }
    
    /** @brief Get key information for diagnostics. */
    String getKeyInfo() const;

    /** @brief Get current request counter value. */
    uint32_t getRequestCount() const { return requestCounter; }
    
    /** @brief Get maximum request limit. */
    uint32_t getRequestLimit() const { return requestLimit; }
    
    /** @brief Reset request counter to zero and save to EEPROM. */
    void resetRequestCounter();

    // =============================
    // HMAC Functions (Public API)
    // =============================
    
    /**
     * @brief Calculate HMAC-SHA256 signature for data.
     * @param data String data to sign.
     * @return Hex-encoded 64-character HMAC signature.
     */
    String calculateHMAC(const String& data);
    
    /**
     * @brief Verify HMAC signature.
     * @param data Original string data.
     * @param received_hmac Received signature to verify.
     * @return true if signature matches, false otherwise.
     */
    bool verifyHMAC(const String& data, const String& received_hmac);
    
    // =============================
    // Token Generation
    // =============================
    
    /**
     * @brief Generate random 32-character security token.
     * @return Random alphanumeric token string.
     */
    static String generateToken();
};

/// @brief Global crypto manager instance (defined in WakeLink.ino)
extern CryptoManager crypto;

#endif // CRYPTO_MANAGER_H
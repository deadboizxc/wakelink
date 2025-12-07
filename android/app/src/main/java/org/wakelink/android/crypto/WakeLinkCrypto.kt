package org.wakelink.android.crypto

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import kotlin.experimental.xor

/**
 * WakeLink Protocol v1.0 Cryptography Implementation.
 * 
 * Uses Java's built-in SHA-256 and HMAC, with pure Kotlin ChaCha20.
 * Compatible with firmware CryptoManager.cpp and Python crypto.py.
 */
class WakeLinkCrypto(token: String) {
    
    private val chachaKey: ByteArray
    private val hmacKey: ByteArray
    
    init {
        require(token.length >= 32) { "Token must be ≥32 characters" }
        
        val tokenBytes = token.toByteArray(Charsets.UTF_8)
        val masterKey = MessageDigest.getInstance("SHA-256").digest(tokenBytes)
        
        chachaKey = masterKey.copyOf(32)
        hmacKey = masterKey.copyOf(32)
    }
    
    // ==================== ChaCha20 ====================
    
    private fun chacha20QuarterRound(state: IntArray, a: Int, b: Int, c: Int, d: Int) {
        state[a] = (state[a] + state[b])
        state[d] = rotl(state[d] xor state[a], 16)
        state[c] = (state[c] + state[d])
        state[b] = rotl(state[b] xor state[c], 12)
        state[a] = (state[a] + state[b])
        state[d] = rotl(state[d] xor state[a], 8)
        state[c] = (state[c] + state[d])
        state[b] = rotl(state[b] xor state[c], 7)
    }
    
    private fun rotl(x: Int, n: Int): Int = (x shl n) or (x ushr (32 - n))
    
    private fun chacha20Block(key: ByteArray, nonce: ByteArray, counter: Int): ByteArray {
        val constants = intArrayOf(0x61707865, 0x3320646e, 0x79622d32, 0x6b206574)
        
        val state = IntArray(16)
        
        // Constants (0-3)
        for (i in 0..3) state[i] = constants[i]
        
        // Key (4-11) - little-endian
        for (i in 0..7) {
            state[4 + i] = ByteBuffer.wrap(key, i * 4, 4).order(ByteOrder.LITTLE_ENDIAN).int
        }
        
        // Counter (12)
        state[12] = counter
        
        // Nonce (13-15) - little-endian
        for (i in 0..2) {
            state[13 + i] = ByteBuffer.wrap(nonce, i * 4, 4).order(ByteOrder.LITTLE_ENDIAN).int
        }
        
        val workingState = state.copyOf()
        
        // 20 rounds (10 double rounds)
        repeat(10) {
            // Column rounds
            chacha20QuarterRound(workingState, 0, 4, 8, 12)
            chacha20QuarterRound(workingState, 1, 5, 9, 13)
            chacha20QuarterRound(workingState, 2, 6, 10, 14)
            chacha20QuarterRound(workingState, 3, 7, 11, 15)
            // Diagonal rounds
            chacha20QuarterRound(workingState, 0, 5, 10, 15)
            chacha20QuarterRound(workingState, 1, 6, 11, 12)
            chacha20QuarterRound(workingState, 2, 7, 8, 13)
            chacha20QuarterRound(workingState, 3, 4, 9, 14)
        }
        
        // Add original state
        for (i in 0..15) workingState[i] = (workingState[i] + state[i])
        
        // Convert to bytes (little-endian)
        return ByteBuffer.allocate(64).order(ByteOrder.LITTLE_ENDIAN).apply {
            workingState.forEach { putInt(it) }
        }.array()
    }
    
    private fun chacha20Encrypt(key: ByteArray, nonce: ByteArray, plaintext: ByteArray): ByteArray {
        val ciphertext = ByteArray(plaintext.size)
        var counter = 0
        
        var i = 0
        while (i < plaintext.size) {
            val keyStream = chacha20Block(key, nonce, counter)
            val blockLen = minOf(64, plaintext.size - i)
            
            for (j in 0 until blockLen) {
                ciphertext[i + j] = plaintext[i + j] xor keyStream[j]
            }
            
            counter++
            i += 64
        }
        
        return ciphertext
    }
    
    // ==================== HMAC-SHA256 ====================
    
    private fun hmacSha256(key: ByteArray, data: ByteArray): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        return mac.doFinal(data)
    }
    
    // ==================== Public API ====================
    
    /**
     * Calculate HMAC-SHA256 signature for data string.
     */
    fun calculateHmac(data: String): String {
        return hmacSha256(hmacKey, data.toByteArray(Charsets.UTF_8)).toHex()
    }
    
    /**
     * Verify HMAC signature.
     */
    fun verifyHmac(data: String, signature: String): Boolean {
        return calculateHmac(data).equals(signature, ignoreCase = true)
    }
    
    /**
     * Encrypt plaintext and return hex-encoded payload.
     * Format: [2B length BE] + [ciphertext] + [16B nonce]
     */
    fun createSecurePayload(plaintext: String): String {
        val data = plaintext.toByteArray(Charsets.UTF_8).let {
            if (it.size > 500) it.copyOf(500) else it
        }
        val fullNonce = ByteArray(16).also { SecureRandom().nextBytes(it) }
        val nonce12 = fullNonce.copyOf(12)
        
        val cipher = chacha20Encrypt(chachaKey, nonce12, data)
        
        val packet = ByteBuffer.allocate(2 + cipher.size + 16)
            .order(ByteOrder.BIG_ENDIAN)
            .putShort(data.size.toShort())
            .put(cipher)
            .put(fullNonce)
            .array()
        
        return packet.toHex()
    }
    
    /**
     * Decrypt hex-encoded payload.
     */
    fun decryptPayload(hexPayload: String): Result<String> {
        return try {
            val packet = hexPayload.hexToByteArray()
            
            if (packet.size < 18) {
                return Result.failure(Exception("Packet too short"))
            }
            
            val length = ByteBuffer.wrap(packet, 0, 2).order(ByteOrder.BIG_ENDIAN).short.toInt() and 0xFFFF
            
            if (length > 500 || packet.size < 2 + length + 16) {
                return Result.failure(Exception("Invalid packet size"))
            }
            
            val cipher = packet.copyOfRange(2, 2 + length)
            val fullNonce = packet.copyOfRange(packet.size - 16, packet.size)
            val nonce12 = fullNonce.copyOf(12)
            
            val plainBytes = chacha20Encrypt(chachaKey, nonce12, cipher)
            Result.success(String(plainBytes, Charsets.UTF_8))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    companion object {
        private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
        
        private fun String.hexToByteArray(): ByteArray {
            val len = length
            val data = ByteArray(len / 2)
            var i = 0
            while (i < len) {
                data[i / 2] = ((Character.digit(this[i], 16) shl 4) + Character.digit(this[i + 1], 16)).toByte()
                i += 2
            }
            return data
        }
    }
}

package org.wakelink.android.protocol

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.wakelink.android.crypto.WakeLinkCrypto
import java.util.UUID

/**
 * WakeLink Protocol v1.0 Packet Manager.
 * 
 * Creates and processes signed, encrypted packets compatible with
 * firmware packet.cpp and Python packet.py.
 */
class PacketManager(
    token: String,
    private val deviceId: String
) {
    private val crypto = WakeLinkCrypto(token)
    
    companion object {
        const val PROTOCOL_VERSION = "1.0"
        
        private val json = Json { 
            ignoreUnknownKeys = true
            encodeDefaults = true
            coerceInputValues = true
            isLenient = true
        }
    }
    
    /**
     * Create a signed, encrypted command packet.
     */
    fun createCommandPacket(command: String, data: Map<String, String> = emptyMap()): String {
        // Build inner packet
        val inner = InnerPacket(
            command = command,
            data = data,
            requestId = UUID.randomUUID().toString().take(8),
            timestamp = System.currentTimeMillis() / 1000
        )
        
        val innerJson = json.encodeToString(inner)
        
        // Encrypt inner packet
        val payloadHex = crypto.createSecurePayload(innerJson)
        
        // Calculate HMAC on payload only
        val signature = crypto.calculateHmac(payloadHex)
        
        // Build outer packet
        val outer = OuterPacket(
            deviceId = deviceId,
            payload = payloadHex,
            signature = signature,
            version = PROTOCOL_VERSION
        )
        
        return json.encodeToString(outer)
    }
    
    /**
     * Process incoming signed, encrypted packet.
     */
    fun processIncomingPacket(packetJson: String): Result<InnerPacket> {
        return try {
            val outer = json.decodeFromString<OuterPacket>(packetJson)
            
            // Verify signature
            if (!crypto.verifyHmac(outer.payload, outer.signature)) {
                return Result.failure(Exception("Invalid signature"))
            }
            
            // Decrypt payload
            val decrypted = crypto.decryptPayload(outer.payload)
            if (decrypted.isFailure) {
                return Result.failure(decrypted.exceptionOrNull() ?: Exception("Decryption failed"))
            }
            
            val inner = json.decodeFromString<InnerPacket>(decrypted.getOrThrow())
            Result.success(inner)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Process raw response (may be JSON or plain error string).
     * Returns CommandResponse with counter from outer packet.
     */
    fun processResponse(response: String): CommandResponse {
        // Check for plain error
        if (response.startsWith("ERROR:")) {
            return CommandResponse(
                status = "error",
                error = response.removePrefix("ERROR:")
            )
        }
        
        return try {
            val outer = json.decodeFromString<OuterPacket>(response)
            
            // Verify signature
            if (!crypto.verifyHmac(outer.payload, outer.signature)) {
                return CommandResponse(status = "error", error = "INVALID_SIGNATURE")
            }
            
            // Decrypt payload
            val decrypted = crypto.decryptPayload(outer.payload)
            if (decrypted.isFailure) {
                return CommandResponse(status = "error", error = "DECRYPT_FAILED")
            }
            
            // Parse inner response and add counter from outer packet
            val innerResponse = json.decodeFromString<CommandResponse>(decrypted.getOrThrow())
            innerResponse.copy(counter = outer.counter)
        } catch (e: Exception) {
            CommandResponse(status = "error", error = e.message ?: "UNKNOWN_ERROR")
        }
    }
}

@Serializable
data class InnerPacket(
    val command: String,
    val data: Map<String, String> = emptyMap(),
    @SerialName("request_id") val requestId: String = "",
    val timestamp: Long = 0
)

@Serializable
data class OuterPacket(
    @SerialName("device_id") val deviceId: String = "",
    val payload: String = "",
    val signature: String = "",
    val counter: Int? = null,
    val version: String = "1.0"
)

@Serializable
data class CommandResponse(
    val status: String = "",
    val error: String? = null,
    val result: String? = null,
    val message: String? = null,
    val data: Map<String, String>? = null,
    
    // Counter from outer packet (synced from ESP)
    val counter: Int? = null,
    
    // Device info fields (from cmd_info)
    @SerialName("device_id") val deviceId: String? = null,
    val ip: String? = null,
    val ssid: String? = null,
    val rssi: Int? = null,
    val requests: Int? = null,
    @SerialName("crypto_enabled") val cryptoEnabled: Boolean? = null,
    val mode: String? = null,
    @SerialName("web_enabled") val webEnabled: Boolean? = null,
    @SerialName("cloud_enabled") val cloudEnabled: Boolean? = null,
    @SerialName("cloud_status") val cloudStatus: String? = null,
    @SerialName("free_heap") val freeHeap: Long? = null,
    
    // Crypto info fields (from cmd_crypto_info)
    val enabled: Boolean? = null,
    val limit: Int? = null,
    @SerialName("key_info") val keyInfo: String? = null,
    
    // Token update fields
    @SerialName("new_token") val newToken: String? = null,
    
    // Wake/OTA fields
    val mac: String? = null,
    val timeout: Int? = null,
    
    // Web control fields
    val connected: Boolean? = null,
    val url: String? = null,
    
    // Other
    val version: String? = null,
    val command: String? = null
)

package org.wakelink.android.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.wakelink.android.data.CommandResult
import org.wakelink.android.data.Device
import org.wakelink.android.protocol.PacketManager
import java.util.concurrent.TimeUnit

/**
 * Cloud Client for HTTP/WSS relay communication.
 * Mirrors Python client's CloudClient with push/pull endpoints.
 */
class CloudClient(private val device: Device) {
    
    private val packetManager = PacketManager(device.token, device.deviceId)
    
    private val json = Json { 
        ignoreUnknownKeys = true
        encodeDefaults = true
    }
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(35, TimeUnit.SECONDS) // Extra time for long polling
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    
    companion object {
        private const val DEFAULT_CLOUD_URL = "https://wakelink.deadboizxc.org"
        private val JSON_MEDIA_TYPE = "application/json".toMediaType()
    }
    
    /**
     * Send command via cloud relay (HTTP push/pull).
     */
    suspend fun sendCommand(
        command: String,
        data: Map<String, String> = emptyMap()
    ): CommandResult = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        val baseUrl = device.cloudUrl ?: DEFAULT_CLOUD_URL
        
        try {
            // Create encrypted packet
            val innerPacket = packetManager.createCommandPacket(command, data)
            val outerJson = json.decodeFromString<OuterPacketDto>(innerPacket)
            
            // Push to device
            val pushBody = PushRequest(
                deviceId = device.deviceId,
                payload = outerJson.payload,
                signature = outerJson.signature,
                version = "1.0",
                direction = "to_device"
            )
            
            val pushRequest = Request.Builder()
                .url("$baseUrl/api/push")
                .addHeader("Authorization", "Bearer ${device.apiToken ?: ""}")
                .addHeader("Content-Type", "application/json")
                .post(json.encodeToString(pushBody).toRequestBody(JSON_MEDIA_TYPE))
                .build()
            
            val pushResponse = client.newCall(pushRequest).execute()
            if (!pushResponse.isSuccessful) {
                return@withContext CommandResult(
                    success = false,
                    status = "error",
                    error = "Push failed: ${pushResponse.code}",
                    latencyMs = System.currentTimeMillis() - startTime
                )
            }
            
            // Pull response (with long polling)
            val pullBody = PullRequest(
                deviceId = device.deviceId,
                direction = "to_client",
                wait = 30
            )
            
            val pullRequest = Request.Builder()
                .url("$baseUrl/api/pull")
                .addHeader("Authorization", "Bearer ${device.apiToken ?: ""}")
                .addHeader("Content-Type", "application/json")
                .post(json.encodeToString(pullBody).toRequestBody(JSON_MEDIA_TYPE))
                .build()
            
            val pullResponse = client.newCall(pullRequest).execute()
            val pullResponseBody = pullResponse.body?.string() ?: ""
            
            if (!pullResponse.isSuccessful) {
                return@withContext CommandResult(
                    success = false,
                    status = "error",
                    error = "Pull failed: ${pullResponse.code}",
                    latencyMs = System.currentTimeMillis() - startTime
                )
            }
            
            val latency = System.currentTimeMillis() - startTime
            
            // Parse pull response
            val pullResult = json.decodeFromString<PullResponse>(pullResponseBody)
            
            if (pullResult.messages.isEmpty()) {
                return@withContext CommandResult(
                    success = false,
                    status = "timeout",
                    error = "No response from device",
                    latencyMs = latency
                )
            }
            
            // Process first message
            val message = pullResult.messages.first()
            val requestCounterPart = message.requestCounter?.let { ",\"request_counter\":$it" } ?: ""
            val responsePacket = """{"device_id":"${device.deviceId}","payload":"${message.payload}","signature":"${message.signature}"$requestCounterPart,"version":"1.0"}"""
            
            val result = packetManager.processResponse(responsePacket)
            
            CommandResult(
                success = result.status == "success",
                status = result.status,
                data = buildResponseData(result),
                error = result.error,
                latencyMs = latency
            )
        } catch (e: Exception) {
            CommandResult(
                success = false,
                status = "error",
                error = e.message ?: "Cloud request failed",
                latencyMs = System.currentTimeMillis() - startTime
            )
        }
    }
    
    private fun buildResponseData(result: org.wakelink.android.protocol.CommandResponse): Map<String, Any?> {
        return buildMap {
            // Request counter from ESP (synced in outer packet)
            result.requestCounter?.let { put("request_counter", it) }
            
            // Basic result fields
            result.result?.let { put("result", it) }
            result.message?.let { put("message", it) }
            
            // Device info fields
            result.deviceId?.let { put("device_id", it) }
            result.ip?.let { put("ip", it) }
            result.ssid?.let { put("ssid", it) }
            result.rssi?.let { put("rssi", it) }
            result.requestCounterInfo?.let { put("request_counter", it) }
            result.cryptoEnabled?.let { put("crypto_enabled", it) }
            result.mode?.let { put("mode", it) }
            result.webEnabled?.let { put("web_enabled", it) }
            result.cloudEnabled?.let { put("cloud_enabled", it) }
            result.cloudStatus?.let { put("cloud_status", it) }
            result.freeHeap?.let { put("free_heap", it) }
            
            // Crypto info fields
            result.enabled?.let { put("enabled", it) }
            result.requestLimit?.let { put("request_limit", it) }
            result.keyInfo?.let { put("key_info", it) }
            
            // Token fields
            result.newToken?.let { put("new_token", it) }
            
            // Wake/OTA fields
            result.mac?.let { put("mac", it) }
            result.timeout?.let { put("timeout", it) }
            
            // Web control fields
            result.connected?.let { put("connected", it) }
            result.url?.let { put("url", it) }
            
            // Other
            result.version?.let { put("version", it) }
            result.command?.let { put("command", it) }
            
            // Custom data map
            result.data?.forEach { (k, v) -> put(k, v) }
        }
    }
}

@Serializable
private data class OuterPacketDto(
    @SerialName("device_id") val deviceId: String = "",
    val payload: String = "",
    val signature: String = "",
    val version: String = "1.0"
)

@Serializable
private data class PushRequest(
    @SerialName("device_id") val deviceId: String,
    val payload: String,
    val signature: String,
    val version: String,
    val direction: String
)

@Serializable
private data class PullRequest(
    @SerialName("device_id") val deviceId: String,
    val direction: String,
    val wait: Int
)

@Serializable
private data class PullResponse(
    val status: String = "",
    @SerialName("device_id") val deviceId: String = "",
    val messages: List<MessageDto> = emptyList(),
    val count: Int = 0
)

@Serializable
private data class MessageDto(
    @SerialName("device_id") val deviceId: String = "",
    val payload: String = "",
    val signature: String = "",
    @SerialName("request_counter") val requestCounter: Int? = null
)

@Serializable
private data class RegisterDeviceRequest(
    @SerialName("device_id") val deviceId: String,
    @SerialName("device_data") val deviceData: DeviceData
)

@Serializable
private data class DeviceData(
    val name: String,
    @SerialName("device_token") val deviceToken: String
)

@Serializable
data class RegisterResponse(
    val status: String = "",
    val message: String? = null,
    val error: String? = null
)

/**
 * Standalone function to register device on cloud server.
 * This is separate because we need to call it before device object exists.
 */
suspend fun registerDeviceOnCloud(
    cloudUrl: String,
    apiToken: String,
    deviceId: String,
    deviceName: String,
    deviceToken: String
): RegisterResponse = withContext(Dispatchers.IO) {
    val json = Json { ignoreUnknownKeys = true }
    val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()
    
    try {
        val requestBody = RegisterDeviceRequest(
            deviceId = deviceId,
            deviceData = DeviceData(
                name = deviceName,
                deviceToken = deviceToken
            )
        )
        
        val request = Request.Builder()
            .url("$cloudUrl/api/register_device")
            .addHeader("Authorization", "Bearer $apiToken")
            .addHeader("Content-Type", "application/json")
            .post(json.encodeToString(requestBody).toRequestBody("application/json".toMediaType()))
            .build()
        
        val response = client.newCall(request).execute()
        val responseBody = response.body?.string() ?: ""
        
        if (!response.isSuccessful) {
            return@withContext RegisterResponse(
                status = "error",
                error = "HTTP ${response.code}: $responseBody"
            )
        }
        
        json.decodeFromString<RegisterResponse>(responseBody)
    } catch (e: Exception) {
        RegisterResponse(
            status = "error",
            error = e.message ?: "Registration failed"
        )
    }
}

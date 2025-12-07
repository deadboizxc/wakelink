package org.wakelink.android.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.wakelink.android.data.CommandResult
import org.wakelink.android.data.Device
import org.wakelink.android.protocol.PacketManager
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.Socket

/**
 * TCP Handler for direct local network communication.
 * Connects to device on port 99 (default).
 */
class TcpHandler(private val device: Device) {
    
    private val packetManager = PacketManager(device.token, device.deviceId)
    
    companion object {
        private const val DEFAULT_TIMEOUT = 10_000 // 10 seconds
    }
    
    /**
     * Send command to device via TCP.
     */
    suspend fun sendCommand(
        command: String, 
        data: Map<String, String> = emptyMap()
    ): CommandResult = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        
        val ip = device.ip ?: return@withContext CommandResult(
            success = false,
            status = "error",
            error = "No IP address configured"
        )
        
        try {
            Socket(ip, device.port).use { socket ->
                socket.soTimeout = DEFAULT_TIMEOUT
                
                val writer = PrintWriter(socket.getOutputStream(), true)
                val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
                
                // Create and send encrypted packet
                val packet = packetManager.createCommandPacket(command, data)
                writer.println(packet)
                
                // Read response
                val response = reader.readLine() ?: return@withContext CommandResult(
                    success = false,
                    status = "error",
                    error = "No response from device"
                )
                
                val latency = System.currentTimeMillis() - startTime
                
                // Process response
                val result = packetManager.processResponse(response)
                
                CommandResult(
                    success = result.status == "success",
                    status = result.status,
                    data = buildResponseData(result),
                    error = result.error,
                    latencyMs = latency
                )
            }
        } catch (e: Exception) {
            CommandResult(
                success = false,
                status = "error",
                error = e.message ?: "Connection failed",
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

package org.wakelink.android.network

import org.wakelink.android.data.CommandResult
import org.wakelink.android.data.Device
import org.wakelink.android.data.TransportMode

/**
 * Unified command executor that selects transport based on device config.
 * Mirrors Python client's WakeLinkCommands class.
 */
class WakeLinkClient(private val device: Device) {
    
    private val tcpHandler by lazy { TcpHandler(device) }
    private val cloudClient by lazy { CloudClient(device) }
    
    /**
     * Send command using configured transport mode.
     */
    suspend fun sendCommand(
        command: String,
        data: Map<String, String> = emptyMap(),
        forceMode: TransportMode? = null
    ): CommandResult {
        val mode = forceMode ?: device.mode
        
        return when (mode) {
            TransportMode.TCP -> tcpHandler.sendCommand(command, data)
            TransportMode.HTTP, TransportMode.WSS -> cloudClient.sendCommand(command, data)
        }
    }
    
    // ==================== Convenience Commands ====================
    
    /** Test device connectivity. */
    suspend fun ping() = sendCommand("ping")
    
    /** Get device information. */
    suspend fun info() = sendCommand("info")
    
    /** Send Wake-on-LAN packet. */
    suspend fun wake(mac: String) = sendCommand("wake", mapOf("mac" to formatMac(mac)))
    
    /** Restart device. */
    suspend fun restart() = sendCommand("restart")
    
    /** Enable OTA mode (30 second window). */
    suspend fun otaStart() = sendCommand("ota_start")
    
    /** Enter AP configuration mode. */
    suspend fun openSetup() = sendCommand("open_setup")
    
    /** Enable web server. */
    suspend fun enableSite() = sendCommand("web_control", mapOf("action" to "enable"))
    
    /** Disable web server. */
    suspend fun disableSite() = sendCommand("web_control", mapOf("action" to "disable"))
    
    /** Get web server status. */
    suspend fun siteStatus() = sendCommand("web_control", mapOf("action" to "status"))
    
    /** Enable cloud (WSS) connection. */
    suspend fun enableCloud() = sendCommand("cloud_control", mapOf("action" to "enable"))
    
    /** Disable cloud (WSS) connection. */
    suspend fun disableCloud() = sendCommand("cloud_control", mapOf("action" to "disable"))
    
    /** Get cloud connection status. */
    suspend fun cloudStatus() = sendCommand("cloud_control", mapOf("action" to "status"))
    
    /** Get cryptography info. */
    suspend fun cryptoInfo() = sendCommand("crypto_info")
    
    /** Generate new device token. */
    suspend fun updateToken() = sendCommand("update_token")
    
    /** Reset request counter. */
    suspend fun resetCounter() = sendCommand("reset_counter")
    
    companion object {
        /**
         * Format MAC address to AA:BB:CC:DD:EE:FF format.
         */
        fun formatMac(mac: String): String {
            val cleaned = mac.replace(Regex("[^a-fA-F0-9]"), "").uppercase()
            if (cleaned.length != 12) return mac
            return cleaned.chunked(2).joinToString(":")
        }
        
        /**
         * Validate MAC address format.
         */
        fun isValidMac(mac: String): Boolean {
            val cleaned = mac.replace(Regex("[^a-fA-F0-9]"), "")
            return cleaned.length == 12
        }
    }
}

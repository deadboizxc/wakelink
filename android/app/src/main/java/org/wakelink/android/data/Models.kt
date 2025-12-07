package org.wakelink.android.data

import kotlinx.serialization.Serializable

/**
 * Device configuration model.
 */
@Serializable
data class Device(
    val name: String,
    val token: String,
    val deviceId: String,
    val ip: String? = null,
    val port: Int = 99,
    val cloudUrl: String? = null,
    val apiToken: String? = null,
    val mode: TransportMode = TransportMode.TCP,
    val addedAt: Long = System.currentTimeMillis()
)

enum class TransportMode {
    TCP,    // Direct local connection
    HTTP,   // Cloud HTTP polling
    WSS     // Cloud WebSocket
}

/**
 * Command execution result.
 */
data class CommandResult(
    val success: Boolean,
    val status: String,
    val data: Map<String, Any?> = emptyMap(),
    val error: String? = null,
    val latencyMs: Long = 0
)

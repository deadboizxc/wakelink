package org.wakelink.android.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "wakelink_devices")

/**
 * Device registry using DataStore.
 * Mirrors Python client's DeviceManager with ~/.wakelink/devices.json
 */
class DeviceRepository(private val context: Context) {
    
    private val json = Json { 
        ignoreUnknownKeys = true 
        prettyPrint = true
    }
    
    companion object {
        private val DEVICES_KEY = stringPreferencesKey("devices")
    }
    
    /**
     * Get all devices as Flow.
     */
    val devicesFlow: Flow<List<Device>> = context.dataStore.data.map { preferences ->
        val devicesJson = preferences[DEVICES_KEY] ?: "[]"
        try {
            json.decodeFromString<List<Device>>(devicesJson)
        } catch (e: Exception) {
            emptyList()
        }
    }
    
    /**
     * Get all devices (suspend).
     */
    suspend fun getDevices(): List<Device> = devicesFlow.first()
    
    /**
     * Get device by name.
     */
    suspend fun getDevice(name: String): Device? = getDevices().find { it.name == name }
    
    /**
     * Add or update device.
     */
    suspend fun saveDevice(device: Device) {
        context.dataStore.edit { preferences ->
            val devices = getDevices().toMutableList()
            val existingIndex = devices.indexOfFirst { it.name == device.name }
            
            if (existingIndex >= 0) {
                devices[existingIndex] = device
            } else {
                devices.add(device)
            }
            
            preferences[DEVICES_KEY] = json.encodeToString(devices)
        }
    }
    
    /**
     * Remove device by name.
     */
    suspend fun removeDevice(name: String) {
        context.dataStore.edit { preferences ->
            val devices = getDevices().filter { it.name != name }
            preferences[DEVICES_KEY] = json.encodeToString(devices)
        }
    }
    
    /**
     * Update device fields.
     */
    suspend fun updateDevice(name: String, update: (Device) -> Device) {
        getDevice(name)?.let { device ->
            saveDevice(update(device))
        }
    }
}

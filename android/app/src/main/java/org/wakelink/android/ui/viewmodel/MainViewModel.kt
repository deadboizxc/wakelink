package org.wakelink.android.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.wakelink.android.data.CommandResult
import org.wakelink.android.data.Device
import org.wakelink.android.data.DeviceRepository
import org.wakelink.android.data.TransportMode
import org.wakelink.android.network.WakeLinkClient

/**
 * Main ViewModel for device management and command execution.
 */
class MainViewModel(application: Application) : AndroidViewModel(application) {
    
    private val repository = DeviceRepository(application)
    
    // Devices list
    private val _devices = MutableStateFlow<List<Device>>(emptyList())
    val devices: StateFlow<List<Device>> = _devices.asStateFlow()
    
    // Selected device
    private val _selectedDevice = MutableStateFlow<Device?>(null)
    val selectedDevice: StateFlow<Device?> = _selectedDevice.asStateFlow()
    
    // Command result
    private val _commandResult = MutableStateFlow<CommandResultState>(CommandResultState.Idle)
    val commandResult: StateFlow<CommandResultState> = _commandResult.asStateFlow()
    
    // Loading state
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    init {
        loadDevices()
    }
    
    private fun loadDevices() {
        viewModelScope.launch {
            repository.devicesFlow.collect { deviceList ->
                _devices.value = deviceList
                // Auto-select first device if none selected
                if (_selectedDevice.value == null && deviceList.isNotEmpty()) {
                    _selectedDevice.value = deviceList.first()
                }
            }
        }
    }
    
    fun selectDevice(device: Device) {
        _selectedDevice.value = device
        _commandResult.value = CommandResultState.Idle
    }
    
    // ==================== Device Management ====================
    
    fun addDevice(
        name: String,
        token: String,
        deviceId: String,
        ip: String?,
        port: Int,
        cloudUrl: String?,
        apiToken: String?,
        mode: TransportMode
    ) {
        viewModelScope.launch {
            val device = Device(
                name = name,
                token = token,
                deviceId = deviceId,
                ip = ip?.takeIf { it.isNotBlank() },
                port = port,
                cloudUrl = cloudUrl?.takeIf { it.isNotBlank() },
                apiToken = apiToken?.takeIf { it.isNotBlank() },
                mode = mode
            )
            repository.saveDevice(device)
        }
    }
    
    fun removeDevice(name: String) {
        viewModelScope.launch {
            repository.removeDevice(name)
            if (_selectedDevice.value?.name == name) {
                _selectedDevice.value = _devices.value.firstOrNull()
            }
        }
    }
    
    fun updateDevice(device: Device) {
        viewModelScope.launch {
            repository.saveDevice(device)
            if (_selectedDevice.value?.name == device.name) {
                _selectedDevice.value = device
            }
        }
    }
    
    // ==================== Commands ====================
    
    fun executeCommand(command: DeviceCommand) {
        val device = _selectedDevice.value ?: return
        
        viewModelScope.launch {
            _isLoading.value = true
            _commandResult.value = CommandResultState.Loading(command.displayName)
            
            try {
                val client = WakeLinkClient(device)
                val result = when (command) {
                    is DeviceCommand.Ping -> client.ping()
                    is DeviceCommand.Info -> client.info()
                    is DeviceCommand.Wake -> client.wake(command.mac)
                    is DeviceCommand.Restart -> client.restart()
                    is DeviceCommand.OtaStart -> client.otaStart()
                    is DeviceCommand.OpenSetup -> client.openSetup()
                    is DeviceCommand.EnableSite -> client.enableSite()
                    is DeviceCommand.DisableSite -> client.disableSite()
                    is DeviceCommand.SiteStatus -> client.siteStatus()
                    is DeviceCommand.EnableCloud -> client.enableCloud()
                    is DeviceCommand.DisableCloud -> client.disableCloud()
                    is DeviceCommand.CloudStatus -> client.cloudStatus()
                    is DeviceCommand.CryptoInfo -> client.cryptoInfo()
                    is DeviceCommand.UpdateToken -> client.updateToken()
                    is DeviceCommand.ResetCounter -> client.resetCounter()
                }
                
                _commandResult.value = CommandResultState.Success(command.displayName, result)
                
                // Update token in device if command was update_token
                if (command is DeviceCommand.UpdateToken && result.success) {
                    result.data["new_token"]?.toString()?.let { newToken ->
                        updateDevice(device.copy(token = newToken))
                    }
                }
            } catch (e: Exception) {
                _commandResult.value = CommandResultState.Error(
                    command.displayName,
                    e.message ?: "Unknown error"
                )
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun clearResult() {
        _commandResult.value = CommandResultState.Idle
    }
}

sealed class CommandResultState {
    object Idle : CommandResultState()
    data class Loading(val command: String) : CommandResultState()
    data class Success(val command: String, val result: CommandResult) : CommandResultState()
    data class Error(val command: String, val error: String) : CommandResultState()
}

sealed class DeviceCommand(val displayName: String) {
    object Ping : DeviceCommand("Ping")
    object Info : DeviceCommand("Info")
    data class Wake(val mac: String) : DeviceCommand("Wake")
    object Restart : DeviceCommand("Restart")
    object OtaStart : DeviceCommand("OTA Start")
    object OpenSetup : DeviceCommand("Open Setup")
    object EnableSite : DeviceCommand("Enable Site")
    object DisableSite : DeviceCommand("Disable Site")
    object SiteStatus : DeviceCommand("Site Status")
    object EnableCloud : DeviceCommand("Enable Cloud")
    object DisableCloud : DeviceCommand("Disable Cloud")
    object CloudStatus : DeviceCommand("Cloud Status")
    object CryptoInfo : DeviceCommand("Crypto Info")
    object UpdateToken : DeviceCommand("Update Token")
    object ResetCounter : DeviceCommand("Reset Counter")
}

package org.wakelink.android.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.wakelink.android.data.Device
import org.wakelink.android.data.TransportMode
import org.wakelink.android.ui.theme.*
import org.wakelink.android.ui.viewmodel.CommandResultState
import org.wakelink.android.ui.viewmodel.DeviceCommand
import org.wakelink.android.ui.viewmodel.MainViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    viewModel: MainViewModel,
    onNavigateToAddDevice: () -> Unit,
    onNavigateToDeviceDetails: (Device) -> Unit
) {
    val devices by viewModel.devices.collectAsState()
    val selectedDevice by viewModel.selectedDevice.collectAsState()
    val commandResult by viewModel.commandResult.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    
    var showWakeDialog by remember { mutableStateOf(false) }
    var wakeTargetMac by remember { mutableStateOf("") }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Text(
                        "WakeLink",
                        fontWeight = FontWeight.Bold
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = WakeLinkBackground,
                    titleContentColor = WakeLinkText
                ),
                actions = {
                    IconButton(onClick = onNavigateToAddDevice) {
                        Icon(
                            Icons.Default.Add,
                            contentDescription = "Add Device",
                            tint = WakeLinkPrimary
                        )
                    }
                }
            )
        },
        containerColor = WakeLinkBackground
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // Device selector
            if (devices.isNotEmpty()) {
                DeviceSelector(
                    devices = devices,
                    selectedDevice = selectedDevice,
                    onDeviceSelected = { viewModel.selectDevice(it) }
                )
            }
            
            if (selectedDevice != null) {
                // Quick actions
                QuickActionsRow(
                    device = selectedDevice!!,
                    isLoading = isLoading,
                    onPing = { viewModel.executeCommand(DeviceCommand.Ping) },
                    onInfo = { viewModel.executeCommand(DeviceCommand.Info) },
                    onWake = { showWakeDialog = true },
                    onDetails = { onNavigateToDeviceDetails(selectedDevice!!) }
                )
                
                // Command result
                CommandResultCard(
                    resultState = commandResult,
                    onDismiss = { viewModel.clearResult() }
                )
                
                // All commands
                CommandsGrid(
                    isLoading = isLoading,
                    onCommand = { viewModel.executeCommand(it) }
                )
            } else {
                // Empty state
                EmptyState(onAddDevice = onNavigateToAddDevice)
            }
        }
    }
    
    // Wake dialog
    if (showWakeDialog) {
        WakeDialog(
            mac = wakeTargetMac,
            onMacChange = { wakeTargetMac = it },
            onConfirm = {
                viewModel.executeCommand(DeviceCommand.Wake(wakeTargetMac))
                showWakeDialog = false
                wakeTargetMac = ""
            },
            onDismiss = {
                showWakeDialog = false
                wakeTargetMac = ""
            }
        )
    }
}

@Composable
fun DeviceSelector(
    devices: List<Device>,
    selectedDevice: Device?,
    onDeviceSelected: (Device) -> Unit
) {
    LazyRow(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(devices) { device ->
            val isSelected = device.name == selectedDevice?.name
            
            FilterChip(
                selected = isSelected,
                onClick = { onDeviceSelected(device) },
                label = { Text(device.name) },
                leadingIcon = {
                    Icon(
                        when (device.mode) {
                            TransportMode.TCP -> Icons.Default.Wifi
                            TransportMode.HTTP -> Icons.Default.Cloud
                            TransportMode.WSS -> Icons.Default.Bolt
                        },
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = WakeLinkPrimary,
                    selectedLabelColor = WakeLinkText,
                    containerColor = WakeLinkCard,
                    labelColor = WakeLinkTextSecondary
                )
            )
        }
    }
}

@Composable
fun QuickActionsRow(
    device: Device,
    isLoading: Boolean,
    onPing: () -> Unit,
    onInfo: () -> Unit,
    onWake: () -> Unit,
    onDetails: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        colors = CardDefaults.cardColors(containerColor = WakeLinkCard),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        device.name,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = WakeLinkText
                    )
                    Text(
                        device.ip ?: device.cloudUrl ?: "No address",
                        style = MaterialTheme.typography.bodyMedium,
                        color = WakeLinkTextSecondary
                    )
                }
                
                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    ModeChip(device.mode)
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                QuickActionButton(
                    icon = Icons.Default.NetworkPing,
                    label = "Ping",
                    enabled = !isLoading,
                    onClick = onPing
                )
                QuickActionButton(
                    icon = Icons.Default.Info,
                    label = "Info",
                    enabled = !isLoading,
                    onClick = onInfo
                )
                QuickActionButton(
                    icon = Icons.Default.Power,
                    label = "Wake",
                    enabled = !isLoading,
                    onClick = onWake
                )
                QuickActionButton(
                    icon = Icons.Default.Settings,
                    label = "Details",
                    enabled = true,
                    onClick = onDetails
                )
            }
        }
    }
}

@Composable
fun ModeChip(mode: TransportMode) {
    val (color, text) = when (mode) {
        TransportMode.TCP -> StatusOnline to "TCP"
        TransportMode.HTTP -> StatusPending to "HTTP"
        TransportMode.WSS -> WakeLinkPrimary to "WSS"
    }
    
    Surface(
        color = color.copy(alpha = 0.2f),
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            color = color,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
fun QuickActionButton(
    icon: ImageVector,
    label: String,
    enabled: Boolean,
    onClick: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable(enabled = enabled, onClick = onClick)
            .padding(8.dp)
    ) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .background(
                    if (enabled) WakeLinkPrimary.copy(alpha = 0.2f) else WakeLinkCard,
                    CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                icon,
                contentDescription = label,
                tint = if (enabled) WakeLinkPrimary else WakeLinkTextSecondary,
                modifier = Modifier.size(24.dp)
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = if (enabled) WakeLinkText else WakeLinkTextSecondary
        )
    }
}

@Composable
fun CommandResultCard(
    resultState: CommandResultState,
    onDismiss: () -> Unit
) {
    when (resultState) {
        is CommandResultState.Idle -> {}
        is CommandResultState.Loading -> {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                colors = CardDefaults.cardColors(containerColor = WakeLinkCard)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = WakeLinkPrimary
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        "Executing ${resultState.command}...",
                        color = WakeLinkText
                    )
                }
            }
        }
        is CommandResultState.Success -> {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
                    .clickable { onDismiss() },
                colors = CardDefaults.cardColors(
                    containerColor = StatusSuccess.copy(alpha = 0.15f)
                )
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Default.CheckCircle,
                            contentDescription = null,
                            tint = StatusSuccess
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "${resultState.command}: ${resultState.result.status}",
                            fontWeight = FontWeight.Bold,
                            color = StatusSuccess
                        )
                        Spacer(modifier = Modifier.weight(1f))
                        Text(
                            "${resultState.result.latencyMs}ms",
                            style = MaterialTheme.typography.bodySmall,
                            color = WakeLinkTextSecondary
                        )
                    }
                    
                    if (resultState.result.data.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        resultState.result.data.forEach { (key, value) ->
                            Text(
                                "$key: $value",
                                style = MaterialTheme.typography.bodySmall,
                                color = WakeLinkText
                            )
                        }
                    }
                }
            }
        }
        is CommandResultState.Error -> {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
                    .clickable { onDismiss() },
                colors = CardDefaults.cardColors(
                    containerColor = StatusError.copy(alpha = 0.15f)
                )
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.Error,
                        contentDescription = null,
                        tint = StatusError
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(
                            "${resultState.command} failed",
                            fontWeight = FontWeight.Bold,
                            color = StatusError
                        )
                        Text(
                            resultState.error,
                            style = MaterialTheme.typography.bodySmall,
                            color = WakeLinkTextSecondary
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun CommandsGrid(
    isLoading: Boolean,
    onCommand: (DeviceCommand) -> Unit
) {
    val commands = listOf(
        Triple(Icons.Default.Refresh, "Restart", DeviceCommand.Restart),
        Triple(Icons.Default.SystemUpdate, "OTA", DeviceCommand.OtaStart),
        Triple(Icons.Default.SettingsInputAntenna, "Setup", DeviceCommand.OpenSetup),
        Triple(Icons.Default.Web, "Site On", DeviceCommand.EnableSite),
        Triple(Icons.Default.WebAssetOff, "Site Off", DeviceCommand.DisableSite),
        Triple(Icons.Default.CloudQueue, "Cloud On", DeviceCommand.EnableCloud),
        Triple(Icons.Default.CloudOff, "Cloud Off", DeviceCommand.DisableCloud),
        Triple(Icons.Default.Security, "Crypto", DeviceCommand.CryptoInfo),
        Triple(Icons.Default.VpnKey, "New Token", DeviceCommand.UpdateToken),
    )
    
    LazyColumn(
        modifier = Modifier.padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        item {
            Text(
                "Commands",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = WakeLinkText,
                modifier = Modifier.padding(bottom = 8.dp)
            )
        }
        
        items(commands.chunked(3)) { row ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                row.forEach { (icon, label, command) ->
                    CommandButton(
                        icon = icon,
                        label = label,
                        enabled = !isLoading,
                        onClick = { onCommand(command) },
                        modifier = Modifier.weight(1f)
                    )
                }
                // Fill remaining space if row is not complete
                repeat(3 - row.size) {
                    Spacer(modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
fun CommandButton(
    icon: ImageVector,
    label: String,
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .aspectRatio(1.2f)
            .clickable(enabled = enabled, onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = if (enabled) WakeLinkCard else WakeLinkCard.copy(alpha = 0.5f)
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                icon,
                contentDescription = label,
                tint = if (enabled) WakeLinkPrimary else WakeLinkTextSecondary,
                modifier = Modifier.size(28.dp)
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                label,
                style = MaterialTheme.typography.labelMedium,
                color = if (enabled) WakeLinkText else WakeLinkTextSecondary
            )
        }
    }
}

@Composable
fun EmptyState(onAddDevice: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            Icons.Default.DevicesOther,
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = WakeLinkTextSecondary
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            "No devices configured",
            style = MaterialTheme.typography.titleLarge,
            color = WakeLinkText
        )
        Text(
            "Add your first WakeLink device",
            style = MaterialTheme.typography.bodyMedium,
            color = WakeLinkTextSecondary
        )
        Spacer(modifier = Modifier.height(24.dp))
        Button(
            onClick = onAddDevice,
            colors = ButtonDefaults.buttonColors(containerColor = WakeLinkPrimary)
        ) {
            Icon(Icons.Default.Add, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Add Device")
        }
    }
}

@Composable
fun WakeDialog(
    mac: String,
    onMacChange: (String) -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Wake-on-LAN", color = WakeLinkText) },
        text = {
            Column {
                Text(
                    "Enter MAC address to wake:",
                    color = WakeLinkTextSecondary
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = mac,
                    onValueChange = onMacChange,
                    label = { Text("MAC Address") },
                    placeholder = { Text("AA:BB:CC:DD:EE:FF") },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = WakeLinkPrimary,
                        unfocusedBorderColor = WakeLinkTextSecondary
                    )
                )
            }
        },
        confirmButton = {
            Button(
                onClick = onConfirm,
                enabled = mac.replace(Regex("[^a-fA-F0-9]"), "").length == 12,
                colors = ButtonDefaults.buttonColors(containerColor = WakeLinkPrimary)
            ) {
                Text("Wake")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel", color = WakeLinkTextSecondary)
            }
        },
        containerColor = WakeLinkSurface
    )
}

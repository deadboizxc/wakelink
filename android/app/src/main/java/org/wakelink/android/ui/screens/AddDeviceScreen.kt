package org.wakelink.android.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import org.wakelink.android.data.TransportMode
import org.wakelink.android.ui.theme.*
import org.wakelink.android.ui.viewmodel.MainViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddDeviceScreen(
    viewModel: MainViewModel,
    onNavigateBack: () -> Unit
) {
    var name by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var deviceId by remember { mutableStateOf("") }
    var ip by remember { mutableStateOf("") }
    var port by remember { mutableStateOf("99") }
    var cloudUrl by remember { mutableStateOf("") }
    var apiToken by remember { mutableStateOf("") }
    var mode by remember { mutableStateOf(TransportMode.TCP) }
    
    var nameError by remember { mutableStateOf<String?>(null) }
    var tokenError by remember { mutableStateOf<String?>(null) }
    
    fun validate(): Boolean {
        nameError = if (name.isBlank()) "Name is required" else null
        tokenError = when {
            token.isBlank() -> "Token is required"
            token.length < 32 -> "Token must be at least 32 characters"
            else -> null
        }
        return nameError == null && tokenError == null
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Add Device", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = WakeLinkBackground,
                    titleContentColor = WakeLinkText,
                    navigationIconContentColor = WakeLinkText
                )
            )
        },
        containerColor = WakeLinkBackground
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Mode selector
            Text(
                "Transport Mode",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = WakeLinkText
            )
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                TransportMode.values().forEach { transportMode ->
                    FilterChip(
                        selected = mode == transportMode,
                        onClick = { mode = transportMode },
                        label = { Text(transportMode.name) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = WakeLinkPrimary,
                            containerColor = WakeLinkCard
                        ),
                        modifier = Modifier.weight(1f)
                    )
                }
            }
            
            Divider(color = WakeLinkCard)
            
            // Basic info
            Text(
                "Device Information",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = WakeLinkText
            )
            
            OutlinedTextField(
                value = name,
                onValueChange = { name = it; nameError = null },
                label = { Text("Device Name") },
                placeholder = { Text("my-device") },
                isError = nameError != null,
                supportingText = nameError?.let { { Text(it) } },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = textFieldColors()
            )
            
            OutlinedTextField(
                value = token,
                onValueChange = { token = it; tokenError = null },
                label = { Text("Device Token") },
                placeholder = { Text("32+ character token") },
                isError = tokenError != null,
                supportingText = tokenError?.let { { Text(it) } },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = textFieldColors()
            )
            
            OutlinedTextField(
                value = deviceId,
                onValueChange = { deviceId = it },
                label = { Text("Device ID (optional)") },
                placeholder = { Text("WL12345678") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = textFieldColors()
            )
            
            Divider(color = WakeLinkCard)
            
            // Connection settings based on mode
            if (mode == TransportMode.TCP) {
                Text(
                    "Local Connection",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = WakeLinkText
                )
                
                OutlinedTextField(
                    value = ip,
                    onValueChange = { ip = it },
                    label = { Text("IP Address") },
                    placeholder = { Text("192.168.1.100") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    colors = textFieldColors()
                )
                
                OutlinedTextField(
                    value = port,
                    onValueChange = { port = it },
                    label = { Text("Port") },
                    placeholder = { Text("99") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    colors = textFieldColors()
                )
            } else {
                Text(
                    "Cloud Connection",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = WakeLinkText
                )
                
                OutlinedTextField(
                    value = cloudUrl,
                    onValueChange = { cloudUrl = it },
                    label = { Text("Cloud URL") },
                    placeholder = { Text("https://wakelink.deadboizxc.org") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = textFieldColors()
                )
                
                OutlinedTextField(
                    value = apiToken,
                    onValueChange = { apiToken = it },
                    label = { Text("API Token") },
                    placeholder = { Text("Your API token") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = textFieldColors()
                )
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Save button
            Button(
                onClick = {
                    if (validate()) {
                        viewModel.addDevice(
                            name = name,
                            token = token,
                            deviceId = deviceId.ifBlank { name },
                            ip = ip.ifBlank { null },
                            port = port.toIntOrNull() ?: 99,
                            cloudUrl = cloudUrl.ifBlank { null },
                            apiToken = apiToken.ifBlank { null },
                            mode = mode
                        )
                        onNavigateBack()
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                colors = ButtonDefaults.buttonColors(containerColor = WakeLinkPrimary),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text(
                    "Add Device",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun textFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = WakeLinkPrimary,
    unfocusedBorderColor = WakeLinkTextSecondary,
    focusedLabelColor = WakeLinkPrimary,
    unfocusedLabelColor = WakeLinkTextSecondary,
    cursorColor = WakeLinkPrimary,
    focusedTextColor = WakeLinkText,
    unfocusedTextColor = WakeLinkText
)

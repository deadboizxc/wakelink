package org.wakelink.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import org.wakelink.android.ui.screens.AddDeviceScreen
import org.wakelink.android.ui.screens.HomeScreen
import org.wakelink.android.ui.theme.WakeLinkTheme
import org.wakelink.android.ui.theme.WakeLinkError
import org.wakelink.android.ui.theme.WakeLinkSuccess
import org.wakelink.android.ui.viewmodel.DeviceCommand
import org.wakelink.android.ui.viewmodel.MainViewModel

class MainActivity : ComponentActivity() {
    
    private val viewModel: MainViewModel by viewModels()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            WakeLinkTheme {
                WakeLinkApp(viewModel)
            }
        }
    }
}

sealed class Screen(val route: String) {
    object Home : Screen("home")
    object AddDevice : Screen("add_device")
    object DeviceDetail : Screen("device/{deviceName}") {
        fun createRoute(deviceName: String) = "device/$deviceName"
    }
}

@Composable
fun WakeLinkApp(viewModel: MainViewModel) {
    val navController = rememberNavController()
    
    NavHost(
        navController = navController,
        startDestination = Screen.Home.route
    ) {
        composable(Screen.Home.route) {
            HomeScreen(
                viewModel = viewModel,
                onNavigateToAddDevice = {
                    navController.navigate(Screen.AddDevice.route)
                },
                onNavigateToDeviceDetails = { device ->
                    navController.navigate(Screen.DeviceDetail.createRoute(device.name))
                }
            )
        }
        
        composable(Screen.AddDevice.route) {
            AddDeviceScreen(
                viewModel = viewModel,
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
        
        composable(
            route = Screen.DeviceDetail.route,
            arguments = listOf(navArgument("deviceName") { type = NavType.StringType })
        ) { backStackEntry ->
            val deviceName = backStackEntry.arguments?.getString("deviceName") ?: ""
            DeviceDetailScreen(
                viewModel = viewModel,
                deviceName = deviceName,
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceDetailScreen(
    viewModel: MainViewModel,
    deviceName: String,
    onNavigateBack: () -> Unit
) {
    val devices by viewModel.devices.collectAsState()
    val device = devices.find { it.name == deviceName }
    
    if (device == null) {
        // Show dark background while navigating back
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(org.wakelink.android.ui.theme.WakeLinkBackground)
        )
        LaunchedEffect(Unit) {
            onNavigateBack()
        }
        return
    }
    
    // Select this device
    LaunchedEffect(device) {
        viewModel.selectDevice(device)
    }
    
    var showDeleteDialog by remember { mutableStateOf(false) }
    var showWakeDialog by remember { mutableStateOf(false) }
    var macAddress by remember { mutableStateOf("") }
    
    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            title = { Text("Delete Device") },
            text = { Text("Are you sure you want to delete ${device.name}?") },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.removeDevice(device.name)
                        showDeleteDialog = false
                        onNavigateBack()
                    }
                ) {
                    Text("Delete", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
    
    if (showWakeDialog) {
        AlertDialog(
            onDismissRequest = { showWakeDialog = false },
            title = { Text("Wake Device") },
            text = {
                OutlinedTextField(
                    value = macAddress,
                    onValueChange = { macAddress = it },
                    label = { Text("MAC Address") },
                    placeholder = { Text("AA:BB:CC:DD:EE:FF") },
                    singleLine = true
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.executeCommand(DeviceCommand.Wake(macAddress))
                        showWakeDialog = false
                        macAddress = ""
                    }
                ) {
                    Text("Wake")
                }
            },
            dismissButton = {
                TextButton(onClick = { showWakeDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(device.name) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { showDeleteDialog = true }) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Device Info Card
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Device Information", style = MaterialTheme.typography.titleMedium)
                    Text("ID: ${device.deviceId}")
                    Text("Mode: ${device.mode}")
                    device.ip?.let { Text("IP: $it") }
                    Text("Port: ${device.port}")
                    device.cloudUrl?.let { Text("Cloud: $it") }
                }
            }
            
            // Command Buttons
            Text("Commands", style = MaterialTheme.typography.titleMedium)
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { viewModel.executeCommand(DeviceCommand.Ping) },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Ping")
                }
                
                Button(
                    onClick = { viewModel.executeCommand(DeviceCommand.Info) },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Info")
                }
            }
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { showWakeDialog = true },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Wake")
                }
                
                Button(
                    onClick = { viewModel.executeCommand(DeviceCommand.Restart) },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Restart")
                }
            }
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { viewModel.executeCommand(DeviceCommand.EnableCloud) },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Cloud On")
                }
                
                Button(
                    onClick = { viewModel.executeCommand(DeviceCommand.DisableCloud) },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Cloud Off")
                }
            }
            
            Button(
                onClick = { viewModel.executeCommand(DeviceCommand.CloudStatus) },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Cloud Status")
            }
        }
    }
}

package org.wakelink.android.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = WakeLinkPrimary,
    secondary = WakeLinkSecondary,
    background = WakeLinkBackground,
    surface = WakeLinkSurface,
    onPrimary = WakeLinkText,
    onSecondary = WakeLinkText,
    onBackground = WakeLinkText,
    onSurface = WakeLinkText,
    surfaceVariant = WakeLinkCard
)

@Composable
fun WakeLinkTheme(
    darkTheme: Boolean = true, // Always dark theme
    content: @Composable () -> Unit
) {
    val colorScheme = DarkColorScheme
    val view = LocalView.current
    
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = WakeLinkBackground.toArgb()
            window.navigationBarColor = WakeLinkBackground.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}

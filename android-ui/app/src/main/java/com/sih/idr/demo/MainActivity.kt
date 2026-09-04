package com.sih.idr.demo

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.sih.idr.demo.backend.NavigationMode
import com.sih.idr.demo.backend.SensorForegroundService
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.TelemetryStore
import com.sih.idr.demo.backend.TrackPoint
import com.sih.idr.demo.ui.NavigatorTheme
import com.sih.idr.demo.ui.screens.NavigationScreen

class MainActivity : ComponentActivity() {

    private val requiredPermissions = buildList {
        add(Manifest.permission.ACCESS_FINE_LOCATION)
        add(Manifest.permission.ACCESS_COARSE_LOCATION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            add(Manifest.permission.HIGH_SAMPLING_RATE_SENSORS)
        }
    }.toTypedArray()

    // Permission launcher
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        permissionsGranted = results.values.all { it }
    }

    private var permissionsGranted by mutableStateOf(false)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Edge-to-edge
        WindowCompat.setDecorFitsSystemWindows(window, false)

        // Check permissions on launch
        permissionsGranted = hasAllPermissions()

        setContent {
            NavigatorTheme {
                // Collect live telemetry or fall back to preview data
                val liveTelemetry by TelemetryStore.state.collectAsStateWithLifecycle()

                // Use live data if service is running, otherwise show preview
                val telemetry = if (liveTelemetry.running) liveTelemetry else PREVIEW_TELEMETRY

                var isRecording by remember { mutableStateOf(false) }
                var permsGranted by remember { mutableStateOf(permissionsGranted) }

                // Sync permission state
                LaunchedEffect(permissionsGranted) {
                    permsGranted = permissionsGranted
                }

                // If service is running, sync recording state
                LaunchedEffect(liveTelemetry.running) {
                    if (liveTelemetry.running) isRecording = true
                }

                NavigationScreen(
                    telemetry = telemetry,
                    isRecording = isRecording,
                    permissionsGranted = permsGranted,
                    onStartStop = {
                        if (!permsGranted) {
                            permissionLauncher.launch(requiredPermissions)
                            return@NavigationScreen
                        }

                        if (isRecording) {
                            SensorForegroundService.stop(this@MainActivity)
                            isRecording = false
                        } else {
                            SensorForegroundService.start(this@MainActivity)
                            isRecording = true
                        }
                    }
                )
            }
        }
    }

    override fun onDestroy() {
        // Don't stop the service on rotation — only on real destroy when not recording
        if (isFinishing) {
            SensorForegroundService.stop(this)
        }
        super.onDestroy()
    }

    private fun hasAllPermissions(): Boolean = requiredPermissions.all {
        ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
    }

    companion object {
        /**
         * Static preview telemetry for UI-only mode: shows what the app looks like
         * without needing sensor permissions, a physical device, or the backend running.
         * This is what Android Studio previews and emulator runs display.
         */
        val PREVIEW_TELEMETRY = TelemetryState(
            running = false,
            mode = NavigationMode.INS,
            speedMps = 13.8f,
            yawRad = 0.24f,
            positionNorthM = 164.2f,
            positionEastM = -38.6f,
            uncertaintyM = 18f,
            sampleRateHz = 200f,
            timestampJitterMs = 0.8f,
            satellites = 0,
            accelAvailable = true,
            gyroAvailable = true,
            gnssAvailable = false,
            path = listOf(
                TrackPoint(-82f, -120f),
                TrackPoint(-64f, -98f),
                TrackPoint(-54f, -78f),
                TrackPoint(-40f, -60f),
                TrackPoint(-22f, -42f),
                TrackPoint(-4f, -28f),
                TrackPoint(18f, -18f),
                TrackPoint(38f, -10f),
                TrackPoint(58f, -4f),
                TrackPoint(78f, -8f),
                TrackPoint(104f, -16f),
                TrackPoint(128f, -24f),
                TrackPoint(148f, -32f),
                TrackPoint(164.2f, -38.6f)
            )
        )
    }
}

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
import com.sih.idr.demo.backend.SensorForegroundService
import com.sih.idr.demo.backend.TelemetryStore
import com.sih.idr.demo.ui.NavigatorTheme
import com.sih.idr.demo.ui.components.MapStack
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
        if (permissionsGranted) {
            seedLocationIfPossible()
        }
    }

    private var permissionsGranted by mutableStateOf(false)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Edge-to-edge
        WindowCompat.setDecorFitsSystemWindows(window, false)

        // Whatever the map flavour needs done once per activity (D-121). `osm` does nothing here;
        // `mapbox` configures the Navigation SDK with our location provider and sensors off.
        MapStack.onActivityCreated(this)

        // Check permissions on launch
        permissionsGranted = hasAllPermissions()
        if (permissionsGranted) {
            seedLocationIfPossible()
        }

        setContent {
            val systemDark = androidx.compose.foundation.isSystemInDarkTheme()
            var isDarkTheme by remember { mutableStateOf(systemDark) }
            var courseUpMode by remember { mutableStateOf(false) }

            // The one source of telemetry there is. Before the service starts this is a
            // default-constructed TelemetryState -- zeros, INITIALIZING, an empty path -- and
            // that empty state is what the screen shows. D-080: a surface with no data shows
            // that it has no data. It does not stand in a plausible-looking drive, because a
            // plausible-looking drive is indistinguishable from a real one in a photograph.
            val telemetry by TelemetryStore.state.collectAsStateWithLifecycle()

            NavigatorTheme(darkTheme = isDarkTheme, tunnelMode = telemetry.tunnelModeActive) {
                var isRecording by remember { mutableStateOf(false) }
                var permsGranted by remember { mutableStateOf(permissionsGranted) }

                // Sync permission state
                LaunchedEffect(permissionsGranted) {
                    permsGranted = permissionsGranted
                }

                // If service is running, sync recording state
                LaunchedEffect(telemetry.running) {
                    if (telemetry.running) isRecording = true
                }

                NavigationScreen(
                    telemetry = telemetry,
                    isRecording = isRecording,
                    permissionsGranted = permsGranted,
                    darkTheme = isDarkTheme,
                    onToggleTheme = { isDarkTheme = !isDarkTheme },
                    courseUpMode = courseUpMode,
                    onToggleCourseUp = { courseUpMode = !courseUpMode },
                    onToggleTunnelMode = {
                        SensorForegroundService.toggleTunnelMode()
                    },
                    onResetOrigin = {
                        SensorForegroundService.resetOrigin()
                    },
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

    private fun seedLocationIfPossible() {
        if (hasAllPermissions()) {
            val lm = getSystemService(LOCATION_SERVICE) as? android.location.LocationManager ?: return
            val lastFused = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                try { lm.getLastKnownLocation(android.location.LocationManager.FUSED_PROVIDER) } catch (e: Exception) { null }
            } else null
            val lastGps = try { lm.getLastKnownLocation(android.location.LocationManager.GPS_PROVIDER) } catch (e: Exception) { null }
            val lastNet = try { lm.getLastKnownLocation(android.location.LocationManager.NETWORK_PROVIDER) } catch (e: Exception) { null }
            val loc = lastFused ?: lastGps ?: lastNet
            if (loc != null) {
                TelemetryStore.update {
                    if (!it.running) {
                        it.copy(
                            latitude = loc.latitude,
                            longitude = loc.longitude,
                            originLat = loc.latitude,
                            originLon = loc.longitude
                        )
                    } else it
                }
            }
        }
    }

    companion object {
        // --- what is deliberately NOT here ------------------------------------------------
        // A `PREVIEW_TELEMETRY` constant used to live here and was rendered whenever the service
        // was not running -- which is what the app shows on launch, in Android Studio, and on a
        // phone with no permissions granted. It carried speed 13.8 m/s, uncertainty 18 m, a
        // fourteen-point track, `sampleRateHz = 200f` and `timestampJitterMs = 0.8f`.
        //
        // The last two are the reason this is a decision and not a cleanup. Achieved sample rate
        // and timestamp jitter per device are exactly the numbers HANDOVER.md section 1 says have
        // never been measured on any phone in this project, and 200 Hz is the FOG configuration
        // that D-081 requires captioned as *not demonstrated*. An unmeasured claim rendered in
        // the same typeface as a measured one is the failure D-080 exists to prevent, and a
        // screenshot of it is indistinguishable from evidence.
        //
        // The empty state is the honest preview. If a design needs reviewing without a device,
        // review it empty, or load a real recording through the replay view in `android/`.
    }
}

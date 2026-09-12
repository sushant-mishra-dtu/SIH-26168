package com.sih.idr.demo.backend

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** UI-facing contract. A JNI backend can replace the service without changing the screens. */
data class TelemetryState(
    val running: Boolean = false,
    val mode: NavigationMode = NavigationMode.INIT,
    val speedMps: Float = 0f,
    val yawRad: Float = 0f,
    val positionNorthM: Float = 0f,
    val positionEastM: Float = 0f,
    val uncertaintyM: Float = 3.5f,
    val sampleRateHz: Float = 0f,
    val timestampJitterMs: Float = 0f,
    val satellites: Int = 0,
    val lastSensorAgeMs: Long = 0,
    val accelAvailable: Boolean = false,
    val gyroAvailable: Boolean = false,
    val gnssAvailable: Boolean = false,
    val tunnelModeActive: Boolean = false,
    val stepCount: Int = 0,
    val latitude: Double = 28.6129,
    val longitude: Double = 77.2295,
    val originLat: Double = 28.6129,
    val originLon: Double = 77.2295,
    val path: List<TrackPoint> = emptyList()
)

enum class NavigationMode(val label: String) {
    GNSS("GNSS LOCK"),
    INS("INS COAST"),
    INIT("INITIALIZING")
}

data class TrackPoint(val northM: Float, val eastM: Float)

object TelemetryStore {
    private val mutableState = MutableStateFlow(TelemetryState())
    val state: StateFlow<TelemetryState> = mutableState.asStateFlow()

    fun update(transform: (TelemetryState) -> TelemetryState) {
        mutableState.value = transform(mutableState.value)
    }

    fun reset() {
        mutableState.value = TelemetryState()
    }
}

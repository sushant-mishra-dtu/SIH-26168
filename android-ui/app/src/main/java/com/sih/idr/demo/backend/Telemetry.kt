package com.sih.idr.demo.backend

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * UI-facing contract. A JNI backend can replace the service without changing the screens.
 *
 * **Position uncertainty is carried as a 2x2 covariance, not a radius** (D-125,
 * `docs/UI_UX_NAVIGATION_PLAN.md` section 7.2). The InEKF's position uncertainty is an ellipse whose
 * long axis is lateral -- AGENTS.md: lateral error is about half of b_g times v times t squared -- and
 * a scalar cannot carry that. [uncertaintyM] stays as the one number the metric card prints
 * (1 sigma along the ellipse's major axis); [covNorthM2], [covNorthEastM2] and [covEastM2] are what the
 * map draws and what a map matcher is handed as `horizontalAccuracy`. The producer of the state
 * keeps the two consistent; the view never derives one from the other.
 */
data class TelemetryState(
    val running: Boolean = false,
    val mode: NavigationMode = NavigationMode.INIT,
    val speedMps: Float = 0f,
    val yawRad: Float = 0f,
    val positionNorthM: Float = 0f,
    val positionEastM: Float = 0f,
    /** 1 sigma along the major axis of the position covariance ellipse, metres. */
    val uncertaintyM: Float = DEFAULT_SIGMA_M,
    /** North-North element of the position covariance, m^2, filter frame (north, east). */
    val covNorthM2: Float = DEFAULT_SIGMA_M * DEFAULT_SIGMA_M,
    /** North-East cross term of the position covariance, m^2. Zero means axis-aligned. */
    val covNorthEastM2: Float = 0f,
    /** East-East element of the position covariance, m^2. */
    val covEastM2: Float = DEFAULT_SIGMA_M * DEFAULT_SIGMA_M,
    /** `SystemClock.elapsedRealtime()` at which the pose above was produced; 0 before the first. */
    val poseElapsedMs: Long = 0L,
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
    val path: List<TrackPoint> = emptyList(),
    val totalDistanceM: Float = 0f,
    val tripDurationSec: Long = 0L
) {
    companion object {
        /** The estimator's prior before any fix, metres. Also what a reset returns to. */
        const val DEFAULT_SIGMA_M = 3.5f
    }
}

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

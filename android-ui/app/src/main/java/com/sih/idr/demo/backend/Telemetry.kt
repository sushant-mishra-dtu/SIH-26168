package com.sih.idr.demo.backend

import com.sih.idr.demo.backend.routing.NavigationRoute
import com.sih.idr.demo.backend.tunnel.FixVerdict
import com.sih.idr.demo.backend.tunnel.TunnelFix
import com.sih.idr.demo.backend.tunnel.TunnelOverride
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.backend.tunnel.TunnelTrigger
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
    /** True while the tunnel machine suppresses GNSS (`TUNNEL_ACTIVE_IDR`, `EXIT_VERIFICATION`). */
    val tunnelModeActive: Boolean = false,
    /** The autonomous tunnel machine's state (D-126) and what last moved it. */
    val tunnelState: TunnelState = TunnelState.GNSS_HEALTHY,
    val tunnelTrigger: TunnelTrigger? = null,
    /** The demo's manual override is on: the machine is pinned in tunnel mode. */
    val tunnelForced: Boolean = false,
    /** The demo's manual override mode (AUTO, FORCE_ON, FORCE_OFF). */
    val tunnelOverride: TunnelOverride = TunnelOverride.AUTO,
    /** Map-matched tunnel projection from the bundled asset geometry; null when outside all coverage. */
    val tunnelFix: TunnelFix? = null,
    /** Mean C/N0 of the best four satellites, dB-Hz, as `GnssStatus` last reported; null before any report. */
    val cn0Top4DbHz: Float? = null,
    /** Ambient light, lux, as the sensor last reported; null if the phone has none or it has not fired. */
    val ambientLux: Float? = null,
    /** The estimator's chi-square verdict on the most recent fix, and the normalised innovation squared. */
    val lastFixVerdict: FixVerdict? = null,
    val lastFixChi2: Float? = null,
    /** Gate counts for the outage in progress (or the last one, once it has ended). */
    val outageAcceptedFixes: Int = 0,
    val outageRejectedFixes: Int = 0,
    /** Measured summary of the last completed outage, for the Stage 5 toast (D-124). */
    val lastExit: TunnelExitSummary? = null,
    val stepCount: Int = 0,
    val latitude: Double = 28.6129,
    val longitude: Double = 77.2295,
    val originLat: Double = 28.6129,
    val originLon: Double = 77.2295,
    val path: List<TrackPoint> = emptyList(),
    val totalDistanceM: Float = 0f,
    val tripDurationSec: Long = 0L,
    /** Active destination turn-by-turn route, if selected; null when browsing map freely. */
    val activeRoute: NavigationRoute? = null,
    /** Current maneuver step index in activeRoute. */
    val activeStepIndex: Int = 0
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

/**
 * What can honestly be said about a tunnel outage once GNSS is back (D-124). Every field is
 * measured on the device: the distance dead-reckoned while GNSS was suppressed, how long that
 * lasted, the residual between the dead-reckoned pose and the first fix the gate let through
 * (against a fix, not against truth -- a phone has no truth), and how the gate voted. There is
 * no drift figure and no grade here, and there must not be.
 */
data class TunnelExitSummary(
    val distanceOnIdrM: Float,
    val elapsedMs: Long,
    /** ‖p_IDR − p_GNSS,first accepted‖ in metres; null if no fix was accepted (only forced). */
    val exitResidualM: Float?,
    val acceptedFixes: Int,
    val rejectedFixes: Int,
    /** The first applied fix was a forced acceptance under the anti-lockout rule, not a pass. */
    val reacquiredByForce: Boolean,
    /** `SystemClock.elapsedRealtime()` when the outage ended. */
    val endedAtMs: Long,
)

object TelemetryStore {
    private val mutableState = MutableStateFlow(TelemetryState())
    val state: StateFlow<TelemetryState> = mutableState.asStateFlow()

    fun update(transform: (TelemetryState) -> TelemetryState) {
        mutableState.value = transform(mutableState.value)
    }

    fun reset() {
        mutableState.value = TelemetryState()
    }

    fun setActiveRoute(route: NavigationRoute?) {
        mutableState.value = mutableState.value.copy(
            activeRoute = route,
            activeStepIndex = 0
        )
    }

    fun setStepIndex(index: Int) {
        mutableState.value = mutableState.value.copy(activeStepIndex = index)
    }

    fun clearActiveRoute() {
        mutableState.value = mutableState.value.copy(
            activeRoute = null,
            activeStepIndex = 0
        )
    }
}

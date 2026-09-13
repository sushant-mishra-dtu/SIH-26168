package com.sih.idr.demo.backend.mapbox

import android.app.PendingIntent
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import com.mapbox.common.location.DeviceLocationProvider
import com.mapbox.common.location.GetLocationCallback
import com.mapbox.common.location.Location
import com.mapbox.common.location.LocationObserver
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.TelemetryStore
import com.sih.idr.demo.backend.errorEllipse
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.concurrent.CopyOnWriteArrayList

/**
 * The one location source the Navigation SDK is given (D-123, `docs/UI_UX_NAVIGATION_PLAN.md`
 * section 7.2, rules R1-R3).
 *
 * The SDK ships its own dead reckoning and will extrapolate across any gap in its feed. If it were
 * ever allowed to, a tunnel demo would show Mapbox's estimate and not ours, and nobody could tell
 * from the screen. So this provider:
 *
 * - **R1** emits at a fixed [CADENCE_MS] whether or not the pose changed -- inside a tunnel, at a
 *   stop, always -- so the SDK's extrapolator never sees a gap to fill;
 * - **R2** is registered with `enableSensors(false)` (see [IdrMapboxNavigation]), because with
 *   sensors on the SDK cross-checks our feed against the phone IMU and drops what disagrees;
 * - **R3** fills every field honestly: `horizontalAccuracy` is the 1 sigma major axis of the
 *   reported covariance ellipse, `bearing` is the filter yaw, `speed` the filter speed and the
 *   timestamps are the pose's own session clock, not the moment of emission.
 *
 * It reads [TelemetryStore], so whatever [com.sih.idr.demo.backend.DeadReckoningBackend] is behind
 * that store -- the demo estimator today, the InEKF through JNI later -- is what drives the map.
 * `altitude` is left null until the backend carries a barometric channel; the SDK accepts that.
 */
object InekfLocationProvider : DeviceLocationProvider {
    /** 10 Hz: the filter's output rate. Measure CPU at this rate on the A55 before lowering it. */
    const val CADENCE_MS = 100L

    private const val NAME = "idr-inekf"

    private val observers = CopyOnWriteArrayList<Pair<LocationObserver, Handler>>()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var ticker: Job? = null

    @Volatile
    private var lastEmitted: Location? = null

    override fun getName(): String = NAME

    override fun addLocationObserver(observer: LocationObserver) =
        addLocationObserver(observer, Looper.getMainLooper())

    override fun addLocationObserver(observer: LocationObserver, looper: Looper) {
        observers.add(observer to Handler(looper))
        ensureTicking()
    }

    override fun removeLocationObserver(observer: LocationObserver) {
        observers.removeAll { it.first === observer }
        if (observers.isEmpty()) {
            ticker?.cancel()
            ticker = null
        }
    }

    override fun getLastLocation(callback: GetLocationCallback) {
        callback.run(lastEmitted)
    }

    /** PendingIntent delivery is not supported; the SDK uses observers. */
    override fun requestLocationUpdates(pendingIntent: PendingIntent) = Unit

    override fun removeLocationUpdates(pendingIntent: PendingIntent) = Unit

    private fun ensureTicking() {
        if (ticker?.isActive == true) return
        ticker = scope.launch {
            while (isActive) {
                val state = TelemetryStore.state.value
                // Nothing is emitted before the service has produced a pose: an unset state is
                // the D-080 empty state, and the SDK must not be handed the default coordinates.
                if (state.running && state.poseElapsedMs > 0L) {
                    val location = state.toMapboxLocation()
                    lastEmitted = location
                    val batch = listOf(location)
                    for ((observer, handler) in observers) {
                        handler.post { observer.onLocationUpdateReceived(batch) }
                    }
                }
                delay(CADENCE_MS)
            }
        }
    }
}

/** R3: the InEKF pose as the SDK's `Location`, every field from the state and none invented. */
internal fun TelemetryState.toMapboxLocation(): Location {
    val ellipse = errorEllipse(covNorthM2, covNorthEastM2, covEastM2)
    val bearingDeg = ((Math.toDegrees(yawRad.toDouble()) % 360.0) + 360.0) % 360.0
    // Wall-clock time of the pose, derived from its session clock rather than from "now".
    val poseAgeMs = SystemClock.elapsedRealtime() - poseElapsedMs
    val poseEpochMs = System.currentTimeMillis() - poseAgeMs
    return Location.Builder()
        .latitude(latitude)
        .longitude(longitude)
        .timestamp(poseEpochMs)
        .monotonicTimestamp(poseElapsedMs * 1_000_000L)
        .horizontalAccuracy(ellipse.semiMajorM.toDouble())
        .bearing(bearingDeg)
        .speed(speedMps.toDouble())
        .source(InekfLocationProvider.getName())
        .build()
}

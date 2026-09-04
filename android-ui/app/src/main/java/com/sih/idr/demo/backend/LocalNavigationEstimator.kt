package com.sih.idr.demo.backend

import android.location.Location
import android.os.SystemClock
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Device-side demo estimator. It is deliberately small and deterministic: the production
 * InEKF/JNI implementation can replace this class behind the same service contract.
 */
class LocalNavigationEstimator {
    private var lastTimestampNs = 0L
    private var lastGnssElapsedMs = 0L
    private var origin: Location? = null
    private var northM = 0f
    private var eastM = 0f
    private var speedMps = 0f
    private var yawRad = 0f
    private var uncertaintyM = 7f
    private var lastTrackPointMs = 0L
    private val track = ArrayDeque<TrackPoint>()

    fun onGyro(zRateRadPerSecond: Float, timestampNs: Long): Estimate {
        if (lastTimestampNs != 0L) {
            val dt = ((timestampNs - lastTimestampNs).coerceIn(0L, 250_000_000L)) / 1_000_000_000f
            yawRad = wrapAngle(yawRad + zRateRadPerSecond * dt)
            northM += speedMps * cos(yawRad) * dt
            eastM += speedMps * sin(yawRad) * dt
            if (!hasFreshGnss()) uncertaintyM = (uncertaintyM + 0.08f * sqrt(dt)).coerceAtMost(500f)
            appendTrackPoint()
        }
        lastTimestampNs = timestampNs
        return snapshot()
    }

    fun onLocation(location: Location): Estimate {
        if (origin == null) {
            origin = Location(location)
            northM = 0f
            eastM = 0f
        } else {
            val reference = origin!!
            val distance = reference.distanceTo(location)
            val bearing = reference.bearingTo(location).toRadians()
            val measuredNorth = distance * cos(bearing)
            val measuredEast = distance * sin(bearing)
            northM = measuredNorth
            eastM = measuredEast
            if (location.hasSpeed()) speedMps = location.speed.coerceAtLeast(0f)
            if (speedMps > 1f) yawRad = bearing
        }
        uncertaintyM = location.accuracy.coerceAtLeast(3f)
        lastGnssElapsedMs = SystemClock.elapsedRealtime()
        appendTrackPoint(force = true)
        return snapshot()
    }

    fun snapshot(): Estimate {
        val gnssFresh = hasFreshGnss()
        return Estimate(
            mode = if (gnssFresh) NavigationMode.GNSS else NavigationMode.INS,
            speedMps = speedMps,
            yawRad = yawRad,
            positionNorthM = northM,
            positionEastM = eastM,
            uncertaintyM = uncertaintyM,
            gnssAvailable = gnssFresh,
            path = track.toList()
        )
    }

    private fun hasFreshGnss(): Boolean = lastGnssElapsedMs != 0L &&
        SystemClock.elapsedRealtime() - lastGnssElapsedMs < GNSS_TIMEOUT_MS

    private fun appendTrackPoint(force: Boolean = false) {
        val now = SystemClock.elapsedRealtime()
        if (!force && now - lastTrackPointMs < TRACK_PERIOD_MS) return
        track.addLast(TrackPoint(northM, eastM))
        while (track.size > MAX_TRACK_POINTS) track.removeFirst()
        lastTrackPointMs = now
    }

    private fun wrapAngle(angle: Float): Float {
        var result = angle
        while (result > Math.PI) result -= (Math.PI * 2).toFloat()
        while (result < -Math.PI) result += (Math.PI * 2).toFloat()
        return result
    }

    companion object {
        private const val GNSS_TIMEOUT_MS = 2_500L
        private const val TRACK_PERIOD_MS = 100L
        private const val MAX_TRACK_POINTS = 300
    }
}

data class Estimate(
    val mode: NavigationMode,
    val speedMps: Float,
    val yawRad: Float,
    val positionNorthM: Float,
    val positionEastM: Float,
    val uncertaintyM: Float,
    val gnssAvailable: Boolean,
    val path: List<TrackPoint>
)

private fun Float.toRadians() = this * Math.PI.toFloat() / 180f

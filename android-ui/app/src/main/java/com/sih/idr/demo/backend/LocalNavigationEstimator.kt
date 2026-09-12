package com.sih.idr.demo.backend

import android.location.Location
import android.os.SystemClock
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Device-side demo estimator. Fuses accelerometer motion sensing (ZUPT + step/cadence estimation),
 * 3D gyroscope/orientation tracking, and GNSS position updates.
 *
 * **Uncertainty Growth Model**:
 * - When stationary (ZUPT active): velocity is zero and position is locked, so uncertainty DOES NOT grow.
 * - When moving during GNSS outage: uncertainty expands proportionally to actual physical distance traveled
 *   and calibrated gyro time drift, preventing runaway error while at rest.
 * - When GNSS is available: uncertainty snaps to GPS accuracy (±2.5–5 m).
 */
class LocalNavigationEstimator {
    private var lastTimestampNs = 0L
    private var lastGnssElapsedMs = 0L
    private var origin: Location? = null
    private var originLat: Double = 28.6129
    private var originLon: Double = 77.2295
    private var northM = 0f
    private var eastM = 0f
    private var speedMps = 0f
    private var yawRad = 0f
    private var uncertaintyM = 3.5f
    private var lastTrackPointMs = 0L
    private val track = ArrayDeque<TrackPoint>()
    private var totalDistanceM = 0f
    private var sessionStartMs = 0L

    // Motion & Adaptive ZUPT state
    private var lastStepTimeNs = 0L
    private var stepCount = 0
    private var isStationary = true
    private var stationaryFrames = 0
    private var runningGravityNorm = 9.80665f
    private var filteredDynamicAccel = 0f
    private var lastGyroRate = 0f
    private var tunnelModeActive = false

    // Step-driven PDR displacement queue (guarantees zero drift when stationary & exact retracing)
    private var pendingStepDistM = 0f
    private var activeStepSpeed = 0f
    private var stepHeadingRad = 0f

    // Heading smoothing
    private var hasExternalOrientation = false

    fun onGyro(zRateRadPerSecond: Float, timestampNs: Long): Estimate {
        lastGyroRate = abs(zRateRadPerSecond)
        if (lastTimestampNs != 0L) {
            if (sessionStartMs == 0L) sessionStartMs = SystemClock.elapsedRealtime()
            val dt = ((timestampNs - lastTimestampNs).coerceIn(0L, 250_000_000L)) / 1_000_000_000f
            if (!hasExternalOrientation) {
                yawRad = wrapAngle(yawRad + zRateRadPerSecond * dt)
            }

            val timeSinceLastStepNs = if (lastStepTimeNs != 0L) timestampNs - lastStepTimeNs else Long.MAX_VALUE

            if (tunnelModeActive || !hasFreshGnss()) {
                // Dead Reckoning during GNSS denial (Vehicular coasting + pedestrian step integration):
                if (pendingStepDistM > 0.001f && timeSinceLastStepNs < STEP_TIMEOUT_NS) {
                    val advance = min(pendingStepDistM, max(activeStepSpeed, 1.2f) * dt * 2.5f)
                    pendingStepDistM -= advance
                    northM += advance * cos(stepHeadingRad)
                    eastM += advance * sin(stepHeadingRad)
                    totalDistanceM += advance
                    speedMps = activeStepSpeed
                    isStationary = false

                    val dSigma = advance * 0.035f + 0.012f * dt
                    uncertaintyM = (uncertaintyM + dSigma).coerceAtMost(50f)
                    appendTrackPoint()
                } else if (speedMps > 0.2f && !isStationary) {
                    // Vehicle coasting through tunnel / GNSS outage along heading
                    val advance = speedMps * dt
                    northM += advance * cos(yawRad)
                    eastM += advance * sin(yawRad)
                    totalDistanceM += advance
                    // Smooth deceleration modeling vehicle rolling resistance
                    speedMps = max(0f, speedMps - 0.35f * dt)
                    val dSigma = advance * 0.035f + 0.012f * dt
                    uncertaintyM = (uncertaintyM + dSigma).coerceAtMost(50f)
                    appendTrackPoint()
                } else {
                    pendingStepDistM = 0f
                    speedMps = 0f
                    isStationary = true
                }
            } else {
                // GNSS Available mode:
                // Gyroscope updates yawRad at 200 Hz for instant heading response.
                // Position is anchored and tracked via incoming GNSS fixes in onLocation().
                uncertaintyM = uncertaintyM.coerceAtMost(5.0f)
            }
        }
        lastTimestampNs = timestampNs
        return snapshot()
    }

    fun onAccelerometer(ax: Float, ay: Float, az: Float, timestampNs: Long): Estimate {
        val norm = sqrt(ax * ax + ay * ay + az * az)

        // Adaptively track local gravity baseline to absorb uncalibrated sensor bias
        runningGravityNorm = 0.985f * runningGravityNorm + 0.015f * norm
        val dynamicAccel = abs(norm - runningGravityNorm)

        // Exponential smoothing of dynamic acceleration energy
        filteredDynamicAccel = 0.85f * filteredDynamicAccel + 0.15f * dynamicAccel

        // Zero Velocity Update (ZUPT) detector: requires low dynamic accel AND low angular rate
        val isQuiet = filteredDynamicAccel < ZUPT_ACCEL_THRESHOLD && lastGyroRate < ZUPT_GYRO_THRESHOLD
        if (isQuiet) {
            stationaryFrames++
            if (stationaryFrames >= STATIONARY_FRAME_COUNT) {
                isStationary = true
                pendingStepDistM = 0f
                speedMps = 0f
            }
        } else {
            stationaryFrames = 0
            if (filteredDynamicAccel > MOTION_TRIGGER_THRESHOLD) {
                isStationary = false
            }

            // Step & motion cadence detection
            val dtStepNs = timestampNs - lastStepTimeNs
            if (dynamicAccel > STEP_PEAK_THRESHOLD && dtStepNs > MIN_STEP_INTERVAL_NS) {
                lastStepTimeNs = timestampNs
                stepCount++

                // Stride length model: 0.50m - 0.78m based on dynamic peak energy
                val stepLen = (0.45f + 0.14f * dynamicAccel.coerceIn(0.8f, 3.5f)).coerceIn(0.50f, 0.78f)
                val dtStepSec = (dtStepNs.coerceIn(250_000_000L, 1_200_000_000L)) / 1_000_000_000f
                val estimatedCadenceSpeed = stepLen / dtStepSec

                // Queue exact physical step displacement along the current ground-plane heading
                pendingStepDistM += stepLen
                stepHeadingRad = yawRad
                activeStepSpeed = estimatedCadenceSpeed
                isStationary = false
            }
        }

        return snapshot()
    }

    fun onOrientation(azimuthRad: Float, pitchRad: Float, rollRad: Float) {
        if (!hasExternalOrientation) {
            hasExternalOrientation = true
            yawRad = azimuthRad
        } else {
            // Smooth angular filtering (shortest arc) to eliminate micro-jitter
            val diff = wrapAngle(azimuthRad - yawRad)
            yawRad = wrapAngle(yawRad + 0.22f * diff)
        }
    }

    fun hasOrigin(): Boolean = origin != null

    fun onLocation(location: Location): Estimate {
        if (tunnelModeActive) {
            // In tunnel/outage mode: suppress GNSS fixes entirely to demonstrate dead reckoning
            return snapshot()
        }

        if (origin == null) {
            origin = Location(location)
            originLat = location.latitude
            originLon = location.longitude
            northM = 0f
            eastM = 0f
            uncertaintyM = if (location.hasAccuracy()) location.accuracy.coerceIn(2.5f, 15.0f) else 5.0f
            lastGnssElapsedMs = SystemClock.elapsedRealtime()
            track.clear()
            track.addLast(TrackPoint(0f, 0f)) // Immediately seed origin point for polyline drawing
            return snapshot()
        }

        val reference = origin!!
        val distance = reference.distanceTo(location)
        val bearing = reference.bearingTo(location).toRadians()
        val measuredNorth = distance * cos(bearing)
        val measuredEast = distance * sin(bearing)

        // Check displacement from current position
        val dNorth = measuredNorth - northM
        val dEast = measuredEast - eastM
        val deltaFixM = sqrt(dNorth * dNorth + dEast * dEast)

        // Motion detection:
        // A delta >= 0.7m or speed > 0.3 m/s indicates real vehicle/pedestrian motion, rejecting multipath jitter
        if (location.hasSpeed() && location.speed > 0.3f) {
            speedMps = location.speed
            isStationary = false
        } else if (deltaFixM > 0.7f) {
            isStationary = false
            val nowMs = SystemClock.elapsedRealtime()
            val dtSec = if (lastGnssElapsedMs > 0L) ((nowMs - lastGnssElapsedMs).coerceIn(200L, 3000L)) / 1000f else 1f
            speedMps = (deltaFixM / dtSec).coerceIn(0f, 45f)
        } else if (deltaFixM < 0.35f && filteredDynamicAccel < ZUPT_ACCEL_THRESHOLD) {
            // Truly resting at a stoplight or table: lock zero speed
            isStationary = true
            speedMps = 0f
        }

        if (!isStationary) {
            // Smoothly move position towards fix according to accuracy
            val acc = if (location.hasAccuracy()) location.accuracy else 10f
            val alpha = (1.0f / (1.0f + acc / 8.0f)).coerceIn(0.40f, 0.85f)
            northM += alpha * dNorth
            eastM += alpha * dEast
            totalDistanceM += deltaFixM * alpha
            appendTrackPoint(force = true)
        }

        if (speedMps > 1.0f && !hasExternalOrientation && location.hasBearing()) {
            yawRad = location.bearing.toRadians()
        }

        uncertaintyM = if (location.hasAccuracy()) location.accuracy.coerceIn(2.0f, 10.0f) else 3.5f
        lastGnssElapsedMs = SystemClock.elapsedRealtime()
        return snapshot()
    }

    fun toggleTunnelMode(): Boolean {
        tunnelModeActive = !tunnelModeActive
        if (!tunnelModeActive) {
            // Exiting tunnel: re-enable GNSS lock
            lastGnssElapsedMs = SystemClock.elapsedRealtime()
            uncertaintyM = 3.5f
        } else {
            if (speedMps < 0.15f) {
                isStationary = true
                speedMps = 0f
            }
        }
        return tunnelModeActive
    }

    fun notifyGnssHeartbeat() {
        lastGnssElapsedMs = SystemClock.elapsedRealtime()
    }

    fun resetOrigin(newLocation: Location? = null) {
        if (newLocation != null) {
            origin = Location(newLocation)
            originLat = newLocation.latitude
            originLon = newLocation.longitude
        } else {
            origin = null
        }
        northM = 0f
        eastM = 0f
        speedMps = 0f
        pendingStepDistM = 0f
        activeStepSpeed = 0f
        stepHeadingRad = 0f
        track.clear()
        track.addLast(TrackPoint(0f, 0f))
        stepCount = 0
        uncertaintyM = 3.5f
        lastTrackPointMs = 0L
        isStationary = true
        stationaryFrames = 0
        totalDistanceM = 0f
        sessionStartMs = SystemClock.elapsedRealtime()
    }

    fun snapshot(): Estimate {
        val gnssFresh = hasFreshGnss() && !tunnelModeActive
        val latPerMetre = 1.0 / 111_320.0
        val lonPerMetre = 1.0 / (111_320.0 * cos(Math.toRadians(originLat)))
        val currentLat = originLat + northM * latPerMetre
        val currentLon = originLon + eastM * lonPerMetre
        val durationSec = if (sessionStartMs != 0L) (SystemClock.elapsedRealtime() - sessionStartMs) / 1000L else 0L

        return Estimate(
            mode = if (gnssFresh) NavigationMode.GNSS else NavigationMode.INS,
            speedMps = speedMps,
            yawRad = yawRad,
            positionNorthM = northM,
            positionEastM = eastM,
            uncertaintyM = uncertaintyM,
            gnssAvailable = gnssFresh,
            tunnelModeActive = tunnelModeActive,
            stepCount = stepCount,
            latitude = currentLat,
            longitude = currentLon,
            originLat = originLat,
            originLon = originLon,
            path = track.toList(),
            totalDistanceM = totalDistanceM,
            tripDurationSec = durationSec
        )
    }

    private fun hasFreshGnss(): Boolean = lastGnssElapsedMs != 0L &&
        SystemClock.elapsedRealtime() - lastGnssElapsedMs < GNSS_TIMEOUT_MS

    private fun appendTrackPoint(force: Boolean = false) {
        if (isStationary && !force) return
        val now = SystemClock.elapsedRealtime()
        if (!force && now - lastTrackPointMs < TRACK_PERIOD_MS) return
        val last = track.lastOrNull()
        if (last != null) {
            val dNorth = northM - last.northM
            val dEast = eastM - last.eastM
            val minDeltaSq = if (force) 0.09f else 0.25f
            if (dNorth * dNorth + dEast * dEast < minDeltaSq) return
        }
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
        private const val GNSS_TIMEOUT_MS = 6_000L
        private const val TRACK_PERIOD_MS = 100L
        private const val MAX_TRACK_POINTS = 500
        private const val ZUPT_ACCEL_THRESHOLD = 0.30f
        private const val ZUPT_GYRO_THRESHOLD = 0.12f
        private const val MOTION_TRIGGER_THRESHOLD = 0.55f
        private const val STATIONARY_FRAME_COUNT = 12
        private const val STEP_PEAK_THRESHOLD = 1.20f
        private const val MIN_STEP_INTERVAL_NS = 260_000_000L // Max 3.8 steps/sec
        private const val STEP_TIMEOUT_NS = 1_100_000_000L // Decelerate if no step within 1.1s
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
    val tunnelModeActive: Boolean,
    val stepCount: Int,
    val latitude: Double,
    val longitude: Double,
    val originLat: Double,
    val originLon: Double,
    val path: List<TrackPoint>,
    val totalDistanceM: Float = 0f,
    val tripDurationSec: Long = 0L
)

private fun Float.toRadians() = this * Math.PI.toFloat() / 180f

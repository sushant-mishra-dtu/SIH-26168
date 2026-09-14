package com.sih.idr.demo.backend

import android.location.Location
import android.os.SystemClock
import com.sih.idr.demo.backend.tunnel.FixVerdict
import com.sih.idr.demo.backend.tunnel.TunnelState
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Device-side demo estimator. Fuses accelerometer motion sensing (ZUPT + step/cadence estimation),
 * gyroscope heading propagation, and GNSS position updates.
 *
 * **Heading is course over ground, not where the phone points** (D-127). [CourseTracker] owns it:
 * the turn rate is the gyro's component along the world vertical, the absolute reference is the
 * GNSS course, and the handset's own attitude only ever carries the mount offset. Nothing here
 * steers the track from the phone's orientation, so re-seating the phone at a different angle
 * leaves the traced path where it was.
 *
 * **Speed comes from measurements, not from a 60 ms silence** (D-127). [MotionClassifier] owns the
 * ZUPT and step detection, over durations rather than sample counts and with the pedestrian step
 * model gated off in a vehicle.
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
    private var uncertaintyM = 3.5f
    private var lastTrackPointMs = 0L
    private val track = ArrayDeque<TrackPoint>()
    private var totalDistanceM = 0f
    private var sessionStartMs = 0L

    /** Course over ground and the mount offset (D-127). */
    private val course = CourseTracker()

    /** ZUPT, step detection and the pedestrian/vehicle decision (D-127). */
    private val motion = MotionClassifier()

    // Tunnel machine state (D-126). The machine decides; this estimator only obeys it: while the
    // state suppresses GNSS, fixes are gated and counted but never applied to the pose.
    private var tunnelState = TunnelState.GNSS_HEALTHY
    private var consecutiveRejections = 0
    private var outageStartMs = 0L
    private var outageStartDistanceM = 0f
    private var outageAccepted = 0
    private var outageRejected = 0
    private var outageResidualM: Float? = null
    private var outageForced = false
    private var lastFixVerdict: FixVerdict? = null
    private var lastFixChi2: Float? = null
    private var lastExit: TunnelExitSummary? = null

    // Step-driven PDR displacement queue (guarantees zero drift when stationary & exact retracing)
    private var pendingStepDistM = 0f
    private var activeStepSpeed = 0f
    private var stepHeadingRad = 0f
    private var lastStepTimeNs = 0L

    /**
     * A gyro sample in the **device frame**, all three axes.
     *
     * It used to be the single device-Z rate, which is the turn rate about the world vertical only
     * when the phone is lying flat, and carried the wrong sign even then. [CourseTracker] projects
     * the vector onto gravity instead, so a phone in a cradle, in a pocket or face-down all read
     * the same vehicle turn.
     */
    fun onGyro(gxRadPerSecond: Float, gyRadPerSecond: Float, gzRadPerSecond: Float, timestampNs: Long): Estimate {
        val gyroMag = sqrt(
            gxRadPerSecond * gxRadPerSecond +
                gyRadPerSecond * gyRadPerSecond +
                gzRadPerSecond * gzRadPerSecond
        )
        motion.onGyroMagnitude(gyroMag)
        if (lastTimestampNs != 0L) {
            if (sessionStartMs == 0L) sessionStartMs = SystemClock.elapsedRealtime()
            val dt = ((timestampNs - lastTimestampNs).coerceIn(0L, 250_000_000L)) / 1_000_000_000f
            course.onGyro(gxRadPerSecond, gyRadPerSecond, gzRadPerSecond, dt, timestampNs, speedMps)
            val yawRad = course.headingRad()

            val timeSinceLastStepNs = if (lastStepTimeNs != 0L) timestampNs - lastStepTimeNs else Long.MAX_VALUE

            if (tunnelState.suppressesGnss || !hasFreshGnss()) {
                // Dead Reckoning during GNSS denial (Vehicular coasting + pedestrian step integration):
                if (motion.isStationary) {
                    pendingStepDistM = 0f
                    speedMps = 0f
                } else if (pendingStepDistM > 0.001f && timeSinceLastStepNs < STEP_TIMEOUT_NS) {
                    val advance = min(pendingStepDistM, max(activeStepSpeed, 1.2f) * dt * 2.5f)
                    pendingStepDistM -= advance
                    northM += advance * cos(stepHeadingRad)
                    eastM += advance * sin(stepHeadingRad)
                    totalDistanceM += advance
                    speedMps = activeStepSpeed

                    val dSigma = advance * 0.035f + 0.012f * dt
                    uncertaintyM = (uncertaintyM + dSigma).coerceAtMost(50f)
                    appendTrackPoint()
                } else if (speedMps > 0.2f) {
                    // Vehicle coasting through the outage along the course.
                    val advance = speedMps * dt
                    northM += advance * cos(yawRad)
                    eastM += advance * sin(yawRad)
                    totalDistanceM += advance
                    // Constant velocity is the honest assumption with no speed head in this demo
                    // (AGENTS.md: accelerometer is never integrated for it). The old 0.35 m/s^2
                    // ramp was not a model of anything -- it put a 20 m/s car at a standstill 57 s
                    // into a tunnel, and the track stopped with it. What remains is a slow bleed
                    // so a forgotten outage does not coast forever; ZUPT is what actually stops it.
                    speedMps = max(0f, speedMps - speedMps * dt / COAST_TAU_SEC)
                    val dSigma = advance * 0.035f + 0.012f * dt
                    uncertaintyM = (uncertaintyM + dSigma).coerceAtMost(50f)
                    appendTrackPoint()
                } else {
                    pendingStepDistM = 0f
                    speedMps = 0f
                }
            } else {
                // GNSS Available mode:
                // The course tracks at sensor rate for instant heading response.
                // Position is anchored and tracked via incoming GNSS fixes in onLocation().
                uncertaintyM = uncertaintyM.coerceAtMost(5.0f)
            }
        }
        lastTimestampNs = timestampNs
        return snapshot()
    }

    fun onAccelerometer(ax: Float, ay: Float, az: Float, timestampNs: Long): Estimate {
        val step = motion.onAccelerometer(ax, ay, az, timestampNs)
        if (step != null) {
            // Queue exact physical step displacement along the current course.
            pendingStepDistM += step.strideM
            stepHeadingRad = course.headingRad()
            activeStepSpeed = step.cadenceSpeedMps
            lastStepTimeNs = timestampNs
        }
        return snapshot()
    }

    /**
     * The device->world rotation matrix as `SensorManager.getRotationMatrixFromVector` fills it.
     *
     * This replaces the old `onOrientation(azimuth, ...)`, which handed the estimator the azimuth
     * of the phone's +Y axis and let it *be* the heading. That is what made a cradle angle rotate
     * the whole track, and what made a near-upright portrait phone -- +Y pointing at the sky --
     * swing the heading on a couple of degrees of tilt. The tracker needs the whole matrix: the
     * third row is gravity in the device frame, which is both the turn-rate projection and the
     * evidence that the phone is being handled rather than the vehicle turning.
     */
    fun onAttitude(rotationMatrix: FloatArray, timestampNs: Long) {
        course.onRotationMatrix(rotationMatrix, timestampNs)
    }

    fun hasOrigin(): Boolean = origin != null

    fun onLocation(location: Location): Estimate {
        if (origin == null) {
            // No pose yet, so there is nothing to gate against: the first fix seeds the origin
            // whatever the tunnel machine says, and is reported as accepted with no innovation.
            lastFixVerdict = FixVerdict.ACCEPTED
            lastFixChi2 = null
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

        // Chi-square innovation gate, tunnel doc section 3.5, applied while the machine suppresses
        // GNSS -- the states in which this estimator dead-reckons the pose, so the innovation is
        // against a propagated prediction. Outside them the pose is anchored to the last fix and
        // a 1 Hz fix at highway speed would sit tens of metres from it by construction, so the
        // gate is not applied there (it would reject every fix at speed). S = P + R with this
        // estimator's isotropic P; the InEKF's full block goes through the same function.
        val acc = if (location.hasAccuracy()) location.accuracy.coerceAtLeast(1f) else 10f
        val sVar = uncertaintyM * uncertaintyM + acc * acc
        val chi2 = mahalanobisSquared(dNorth, dEast, sVar, 0f, sVar)
        val gated = tunnelState.suppressesGnss
        val verdict = when {
            !gated -> FixVerdict.ACCEPTED
            chi2 <= CHI2_GATE_2DOF_99 -> FixVerdict.ACCEPTED
            // D-115's anti-lockout rule: a fix rejected this many times running is applied,
            // on the record as forced. Without it a dead-reckoned pose that drifted past the
            // gate's width would never re-acquire.
            consecutiveRejections + 1 >= MAX_CONSECUTIVE_REJECTIONS -> FixVerdict.FORCED
            else -> FixVerdict.REJECTED
        }
        lastFixVerdict = verdict
        lastFixChi2 = chi2
        if (gated) {
            when (verdict) {
                FixVerdict.REJECTED -> {
                    consecutiveRejections++
                    outageRejected++
                }
                FixVerdict.ACCEPTED -> {
                    consecutiveRejections = 0
                    outageAccepted++
                    if (outageResidualM == null) outageResidualM = deltaFixM
                }
                FixVerdict.FORCED -> {
                    consecutiveRejections = 0
                    outageForced = true
                    if (outageResidualM == null) outageResidualM = deltaFixM
                }
            }
            // Evaluated, counted, not applied: the machine decides when fixes move the pose again.
            lastGnssElapsedMs = SystemClock.elapsedRealtime()
            return snapshot()
        }

        // Speed. The receiver's own Doppler speed is the best measurement of it this demo has, so
        // it is taken whenever the fix carries one -- including the small values. It used to be
        // ignored below 0.3 m/s, which sent a crawling vehicle down the fix-differencing path and
        // let the ZUPT detector zero the speedometer against a fix that said otherwise.
        val nowMs = SystemClock.elapsedRealtime()
        if (location.hasSpeed()) {
            speedMps = location.speed.coerceIn(0f, MAX_PLAUSIBLE_SPEED)
        } else if (deltaFixM > 0.7f) {
            // A delta this size is real motion rather than multipath jitter.
            val dtSec = if (lastGnssElapsedMs > 0L) ((nowMs - lastGnssElapsedMs).coerceIn(200L, 3000L)) / 1000f else 1f
            speedMps = (deltaFixM / dtSec).coerceIn(0f, MAX_PLAUSIBLE_SPEED)
        } else if (deltaFixM < 0.35f && motion.dynamicAccelMps2 < MotionClassifier.ZUPT_ACCEL_THRESHOLD) {
            // Truly resting at a stoplight or table: lock zero speed
            speedMps = 0f
        }
        motion.observeSpeed(speedMps)

        if (!motion.isStationary) {
            // Smoothly move position towards fix according to accuracy
            val alpha = (1.0f / (1.0f + acc / 8.0f)).coerceIn(0.40f, 0.85f)
            northM += alpha * dNorth
            eastM += alpha * dEast
            totalDistanceM += deltaFixM * alpha
            appendTrackPoint(force = true)
        }

        // The GNSS course over ground is the only absolute heading here that is about the vehicle.
        // It anchors the course and, through it, re-learns where the phone is pointing relative to
        // the direction of travel -- the mount offset. The tracker decides whether the speed makes
        // the bearing worth believing.
        if (location.hasBearing()) {
            course.onGnssCourse(location.bearing.toRadians(), speedMps)
        }

        uncertaintyM = if (location.hasAccuracy()) location.accuracy.coerceIn(2.0f, 10.0f) else 3.5f
        lastGnssElapsedMs = nowMs
        return snapshot()
    }

    /** The tunnel machine's state, applied by the service after every machine update (D-126). */
    fun setTunnelState(state: TunnelState, nowMs: Long) {
        if (state == tunnelState) return
        val wasSuppressed = tunnelState.suppressesGnss
        tunnelState = state
        if (!wasSuppressed && state.suppressesGnss) {
            // An outage begins: everything the exit summary reports is measured from here.
            outageStartMs = nowMs
            outageStartDistanceM = totalDistanceM
            outageAccepted = 0
            outageRejected = 0
            outageResidualM = null
            outageForced = false
            consecutiveRejections = 0
            if (speedMps < 0.15f) speedMps = 0f
        } else if (wasSuppressed && !state.suppressesGnss) {
            // The outage ends: fixes apply again from the next one. The GNSS branch of onGyro
            // caps the uncertainty as fixes arrive; nothing is reset to a nominal value here.
            lastExit = TunnelExitSummary(
                distanceOnIdrM = totalDistanceM - outageStartDistanceM,
                elapsedMs = nowMs - outageStartMs,
                exitResidualM = outageResidualM,
                acceptedFixes = outageAccepted,
                rejectedFixes = outageRejected,
                reacquiredByForce = outageForced,
                endedAtMs = nowMs
            )
            lastGnssElapsedMs = SystemClock.elapsedRealtime()
        }
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
        lastStepTimeNs = 0L
        track.clear()
        track.addLast(TrackPoint(0f, 0f))
        course.reset()
        motion.reset()
        uncertaintyM = 3.5f
        lastTrackPointMs = 0L
        totalDistanceM = 0f
        sessionStartMs = SystemClock.elapsedRealtime()
        outageStartDistanceM = 0f
        outageAccepted = 0
        outageRejected = 0
        outageResidualM = null
        outageForced = false
        consecutiveRejections = 0
        lastFixVerdict = null
        lastFixChi2 = null
        lastExit = null
    }

    fun snapshot(): Estimate {
        val gnssFresh = hasFreshGnss() && !tunnelState.suppressesGnss
        val latPerMetre = 1.0 / 111_320.0
        val lonPerMetre = 1.0 / (111_320.0 * cos(Math.toRadians(originLat)))
        val currentLat = originLat + northM * latPerMetre
        val currentLon = originLon + eastM * lonPerMetre
        val durationSec = if (sessionStartMs != 0L) (SystemClock.elapsedRealtime() - sessionStartMs) / 1000L else 0L

        // This estimator carries one scalar sigma, so its covariance is isotropic by construction
        // -- sigma squared on the diagonal, no cross term. That is a faithful statement of what it
        // knows, not a measurement of an ellipse: the InEKF behind DeadReckoningBackend will fill
        // all three elements from its P block and the map will draw a real ellipse (D-125).
        val sigmaSq = uncertaintyM * uncertaintyM
        return Estimate(
            mode = if (gnssFresh) NavigationMode.GNSS else NavigationMode.INS,
            speedMps = speedMps,
            yawRad = course.headingRad(),
            headingIsCourse = course.hasCourse,
            mountOffsetRad = if (course.hasMountOffset) course.mountOffsetRad else null,
            attitudeDisturbed = course.isDisturbed,
            motionMode = motion.mode,
            positionNorthM = northM,
            positionEastM = eastM,
            uncertaintyM = uncertaintyM,
            covNorthM2 = sigmaSq,
            covNorthEastM2 = 0f,
            covEastM2 = sigmaSq,
            poseElapsedMs = SystemClock.elapsedRealtime(),
            gnssAvailable = gnssFresh,
            tunnelModeActive = tunnelState.suppressesGnss,
            tunnelState = tunnelState,
            lastFixVerdict = lastFixVerdict,
            lastFixChi2 = lastFixChi2,
            outageAcceptedFixes = outageAccepted,
            outageRejectedFixes = outageRejected,
            lastExit = lastExit,
            stepCount = motion.stepCount,
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
        if (motion.isStationary && !force) return
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

    companion object {
        private const val GNSS_TIMEOUT_MS = 6_000L
        private const val TRACK_PERIOD_MS = 100L
        private const val MAX_TRACK_POINTS = 500
        private const val STEP_TIMEOUT_NS = 1_100_000_000L // Decelerate if no step within 1.1s
        /** Faster than any ground vehicle this is demonstrated in; a fix past it is not a speed. */
        private const val MAX_PLAUSIBLE_SPEED = 60f
        /**
         * Coasting decays with this time constant rather than a fixed ramp: a constant-velocity
         * hold with a slow bleed, not a model of rolling resistance, and honest about it.
         */
        private const val COAST_TAU_SEC = 120f
        /** D-115's rule, mirrored: the fix after this many consecutive rejections is applied, as forced. */
        private const val MAX_CONSECUTIVE_REJECTIONS = 5
    }
}

data class Estimate(
    val mode: NavigationMode,
    val speedMps: Float,
    val yawRad: Float,
    /** True when [yawRad] is a GNSS-anchored course; false while it is only the phone's azimuth. */
    val headingIsCourse: Boolean,
    /** `deviceAzimuth - course`, radians; null until a course and an attitude have both been seen. */
    val mountOffsetRad: Float?,
    /** True while the phone is being handled and the course is held rather than propagated. */
    val attitudeDisturbed: Boolean,
    val motionMode: MotionMode,
    val positionNorthM: Float,
    val positionEastM: Float,
    val uncertaintyM: Float,
    val covNorthM2: Float,
    val covNorthEastM2: Float,
    val covEastM2: Float,
    val poseElapsedMs: Long,
    val gnssAvailable: Boolean,
    val tunnelModeActive: Boolean,
    val tunnelState: TunnelState,
    val lastFixVerdict: FixVerdict?,
    val lastFixChi2: Float?,
    val outageAcceptedFixes: Int,
    val outageRejectedFixes: Int,
    val lastExit: TunnelExitSummary?,
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

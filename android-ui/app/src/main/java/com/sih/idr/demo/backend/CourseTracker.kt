package com.sih.idr.demo.backend

import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.sqrt

/**
 * Course over ground, kept separate from how the phone happens to be held (D-127).
 *
 * The demo estimator used to take its heading straight from the phone's attitude: the azimuth of
 * the device's +Y axis projected onto the ground plane, and the *device-frame* gyro Z axis as the
 * turn rate. Both are statements about the handset, not about the vehicle, and both fail the
 * moment the phone is not lying flat and pointing where the car is going:
 *
 *  - **The turn rate was wrong unless the phone was flat.** A vehicle turn is a rotation about the
 *    *world* vertical. It lands on device Z only when device Z is vertical; in a windscreen cradle
 *    most of it lands on device Y, and the integrated heading is then a fraction of the real turn.
 *    The sign was wrong too: a right-hand-positive rate about world up is *counter*-clockwise seen
 *    from above, so it decreases a compass bearing, and the old code added it.
 *  - **The absolute heading was the phone's, not the car's.** Any fixed mounting angle -- a cradle
 *    canted 30 degrees, a phone face-up in a cup holder -- rotated the whole traced track by that
 *    angle, and the near-vertical portrait case (device +Y pointing at the sky) made the
 *    projection ill-conditioned, so a couple of degrees of tilt swung the heading wildly.
 *
 * So the course is a state of its own here. It is **propagated** by the component of the gyro
 * along the world vertical, **anchored** by the GNSS course over ground whenever the vehicle is
 * moving fast enough for that bearing to mean something, and **frozen** whenever the evidence says
 * the phone is being handled rather than the vehicle turning. What the phone points at is only
 * ever used to carry the mount offset across a re-position, never to steer the track.
 *
 * Four rules do the work, in the order they fire:
 *
 *  1. **Gravity projection.** The yaw rate is `-(omega . u)` with `u` the world-up axis expressed in
 *     the device frame (the third row of the rotation matrix). That is the true rate of turn about
 *     the vertical at any attitude, and the negation puts it in the bearing convention the rest of
 *     the estimator uses (0 = north, +90 degrees = east, clockwise positive).
 *  2. **Stationary freeze.** A vehicle that is not moving is not changing course. Below
 *     [COURSE_INTEGRATION_MIN_SPEED] the course does not integrate at all, which is what stops the
 *     track from spinning when the phone is picked up at a red light.
 *  3. **Handling detection.** The world-up axis is fixed in the *world*; in the *device* frame it
 *     moves only when the handset is tilted. A vehicle turn leaves it where it is. So a tilt rate
 *     over [TILT_DISTURBANCE_RAD_PER_SEC], or a yaw rate no vehicle can produce
 *     ([IMPLAUSIBLE_TURN_RATE_RAD_PER_SEC]), means hands, not steering: the course is held and the
 *     mount offset is re-learned against the *unchanged* course once things settle. Re-seating the
 *     phone therefore changes the offset and leaves the track alone, which is the whole point.
 *  4. **Rate clamp.** What does survive the above is still clamped to
 *     [MAX_VEHICLE_TURN_RATE_RAD_PER_SEC], so a single bad sample cannot put a kink in the track.
 *
 * Pure Kotlin with the clock injected, for the reason `TunnelFsm` is (D-126): a heading rule that
 * cannot be driven from a JUnit test on a laptop is a heading rule nobody can argue about.
 */
class CourseTracker {

    /** Travel heading, bearing convention (0 = north, +pi/2 = east), radians in (-pi, pi]. */
    var courseRad: Float = 0f
        private set

    /** True once a GNSS course over ground has anchored [courseRad] to something real. */
    var hasCourse: Boolean = false
        private set

    /** Azimuth of the device reference axis, bearing convention. What the *phone* points at. */
    var deviceAzimuthRad: Float = 0f
        private set

    var hasDeviceAzimuth: Boolean = false
        private set

    /** `deviceAzimuth - course`: how the phone sits relative to the direction of travel. */
    var mountOffsetRad: Float = 0f
        private set

    var hasMountOffset: Boolean = false
        private set

    /** True while the phone is being handled and the course is held rather than propagated. */
    var isDisturbed: Boolean = false
        private set

    /** Last yaw rate about the world vertical, bearing convention, rad/s. Diagnostics only. */
    var lastYawRateRadPerSec: Float = 0f
        private set

    // World-up axis expressed in the device frame, unit length.
    private var upX = 0f
    private var upY = 0f
    private var upZ = 1f
    private var hasUp = false

    private var lastAttitudeNs = 0L
    private var disturbedUntilNs = 0L

    /**
     * Which device axis (0 = x, 1 = y, 2 = z) the azimuth is read off. Sticky: switched only when
     * the one in use has tipped towards the vertical and another is comfortably horizontal, so the
     * reference does not chatter between two near-equal choices.
     */
    private var refAxis = 1

    /**
     * The full device->world rotation, as `SensorManager.getRotationMatrixFromVector` fills it:
     * row-major, `v_world(ENU) = R * v_device`.
     *
     * The third row is world up in device coordinates, which is rules 1 and 3; the columns are the
     * device axes in world coordinates, which is where the azimuth comes from.
     */
    fun onRotationMatrix(r: FloatArray, timestampNs: Long) {
        if (r.size < 9) return
        val norm = sqrt(r[6] * r[6] + r[7] * r[7] + r[8] * r[8])
        if (norm < 1e-3f) return
        val nx = r[6] / norm
        val ny = r[7] / norm
        val nz = r[8] / norm

        val dt = if (lastAttitudeNs == 0L) {
            0f
        } else {
            ((timestampNs - lastAttitudeNs).coerceIn(0L, MAX_DT_NS)) / 1e9f
        }
        lastAttitudeNs = timestampNs

        if (hasUp && dt > 1e-4f) {
            val dot = (nx * upX + ny * upY + nz * upZ).coerceIn(-1f, 1f)
            if (acos(dot) / dt > TILT_DISTURBANCE_RAD_PER_SEC) {
                disturbedUntilNs = timestampNs + DISTURBANCE_HOLD_NS
            }
        }
        upX = nx
        upY = ny
        upZ = nz
        hasUp = true

        val axis = pickReferenceAxis(r)
        if (axis != refAxis) {
            // The reference direction itself changed, so any offset measured against the old one
            // is meaningless. Re-derive it from the course, which has not moved.
            refAxis = axis
            if (hasCourse) {
                deviceAzimuthRad = axisAzimuth(r, axis)
                hasDeviceAzimuth = true
                mountOffsetRad = wrapAngle(deviceAzimuthRad - courseRad)
                hasMountOffset = true
                updateDisturbance(timestampNs)
                return
            }
        }
        deviceAzimuthRad = axisAzimuth(r, axis)
        hasDeviceAzimuth = true
        updateDisturbance(timestampNs)
    }

    /**
     * A gyro sample, in the device frame, with the speed the estimator currently believes.
     * Returns the course after the update.
     */
    fun onGyro(
        gxRadPerSec: Float,
        gyRadPerSec: Float,
        gzRadPerSec: Float,
        dtSec: Float,
        timestampNs: Long,
        speedMps: Float
    ): Float {
        // Rule 1. Without an attitude the only defensible reading of a single axis is the flat,
        // screen-up case, where device z is world up; the negation is the bearing convention.
        val rate = if (hasUp) {
            -(gxRadPerSec * upX + gyRadPerSec * upY + gzRadPerSec * upZ)
        } else {
            -gzRadPerSec
        }
        lastYawRateRadPerSec = rate

        // Rule 3, second half: a rate no car can turn at is a hand, not a steering wheel.
        if (abs(rate) > IMPLAUSIBLE_TURN_RATE_RAD_PER_SEC) {
            disturbedUntilNs = timestampNs + DISTURBANCE_HOLD_NS
        }
        updateDisturbance(timestampNs)
        if (isDisturbed) return courseRad

        // Rule 2. A stopped vehicle does not change course, whatever the handset is doing.
        if (speedMps < COURSE_INTEGRATION_MIN_SPEED) return courseRad
        if (dtSec <= 0f) return courseRad

        // Rule 4.
        val clamped = rate.coerceIn(-MAX_VEHICLE_TURN_RATE_RAD_PER_SEC, MAX_VEHICLE_TURN_RATE_RAD_PER_SEC)
        courseRad = wrapAngle(courseRad + clamped * dtSec)
        if (hasDeviceAzimuth) {
            // The mount has not moved, so the offset follows the course the gyro just turned.
            mountOffsetRad = wrapAngle(deviceAzimuthRad - courseRad)
            hasMountOffset = true
        }
        return courseRad
    }

    /**
     * The GNSS course over ground. This is the only absolute heading in the system that is about
     * the *vehicle*, so it is what the course is anchored to -- but only above
     * [COURSE_ANCHOR_MIN_SPEED], because a bearing reported at walking pace is the noise in two
     * consecutive fixes and would drag the course around a stationary car.
     */
    fun onGnssCourse(bearingRad: Float, speedMps: Float) {
        if (speedMps < COURSE_ANCHOR_MIN_SPEED) return
        if (!hasCourse) {
            courseRad = wrapAngle(bearingRad)
            hasCourse = true
        } else {
            val diff = wrapAngle(bearingRad - courseRad)
            courseRad = wrapAngle(courseRad + GNSS_ANCHOR_GAIN * diff)
        }
        if (hasDeviceAzimuth) {
            mountOffsetRad = wrapAngle(deviceAzimuthRad - courseRad)
            hasMountOffset = true
        }
    }

    /**
     * The heading the estimator should dead-reckon along. The anchored course once there is one;
     * before that, the phone's own azimuth, which is a guess and is not treated as anything else
     * ([hasCourse] says which is which).
     */
    fun headingRad(): Float = when {
        hasCourse -> courseRad
        hasDeviceAzimuth -> deviceAzimuthRad
        else -> courseRad
    }

    fun reset() {
        courseRad = 0f
        hasCourse = false
        deviceAzimuthRad = 0f
        hasDeviceAzimuth = false
        mountOffsetRad = 0f
        hasMountOffset = false
        isDisturbed = false
        lastYawRateRadPerSec = 0f
        hasUp = false
        upX = 0f
        upY = 0f
        upZ = 1f
        lastAttitudeNs = 0L
        disturbedUntilNs = 0L
        refAxis = 1
    }

    /**
     * On the falling edge of a disturbance, re-learn the mount offset against the course that was
     * held through it. This is what makes "the phone was re-seated at a different angle" cost
     * nothing: the offset absorbs the change and the traced track never turns.
     */
    private fun updateDisturbance(nowNs: Long) {
        val disturbed = nowNs < disturbedUntilNs
        if (isDisturbed && !disturbed && hasCourse && hasDeviceAzimuth) {
            mountOffsetRad = wrapAngle(deviceAzimuthRad - courseRad)
            hasMountOffset = true
        }
        isDisturbed = disturbed
    }

    companion object {
        /**
         * Below this the course is held: a stopped vehicle has no course to change, and this is
         * the rule that stops a handset picked up at a red light from rotating the track. 0.7 m/s
         * is a slow walk, under the 1 m/s at which a GNSS bearing starts to be meaningful.
         */
        const val COURSE_INTEGRATION_MIN_SPEED = 0.7f

        /**
         * A GNSS bearing below this is the difference of two noisy fixes rather than a direction
         * of travel. 2 m/s is ~7 km/h.
         */
        const val COURSE_ANCHOR_MIN_SPEED = 2.0f

        /** Per-fix pull towards the GNSS course. At 1 Hz this closes a 90 degree error in ~8 s. */
        const val GNSS_ANCHOR_GAIN = 0.25f

        /**
         * 60 deg/s. A car at 10 m/s on a 10 m radius -- a tight roundabout -- turns at 57 deg/s,
         * so this passes every vehicle manoeuvre and clamps single-sample spikes.
         */
        const val MAX_VEHICLE_TURN_RATE_RAD_PER_SEC = 1.05f

        /** 200 deg/s. Nothing a vehicle does; a hand turning the phone over, routinely. */
        const val IMPLAUSIBLE_TURN_RATE_RAD_PER_SEC = 3.5f

        /**
         * 25 deg/s of *tilt*. The world-up axis does not move in the device frame while the
         * vehicle turns, so any sustained motion of it is the handset being moved. Road camber and
         * speed bumps are well under this.
         */
        const val TILT_DISTURBANCE_RAD_PER_SEC = 0.44f

        /** How long after the last handling evidence the course stays frozen: 0.8 s. */
        const val DISTURBANCE_HOLD_NS = 800_000_000L

        private const val MAX_DT_NS = 250_000_000L

        /**
         * Pick the device axis whose azimuth is best conditioned -- the one furthest from vertical.
         * Sticky, so that a phone wobbling between two near-equal choices does not chatter between
         * two references 90 degrees apart.
         */
        internal fun pickReferenceAxis(r: FloatArray, current: Int): Int {
            val vertical = floatArrayOf(abs(r[6]), abs(r[7]), abs(r[8]))
            if (vertical[current] < AXIS_SWITCH_HIGH) return current
            var best = current
            for (i in 0..2) {
                if (vertical[i] < vertical[best]) best = i
            }
            return if (vertical[best] < AXIS_SWITCH_LOW) best else current
        }

        /** Azimuth of device axis [axis], bearing convention: `atan2(east, north)` of its world image. */
        internal fun axisAzimuth(r: FloatArray, axis: Int): Float =
            atan2(r[axis], r[3 + axis])

        /** The device axis is within ~32 degrees of vertical: time to look for a better one. */
        private const val AXIS_SWITCH_HIGH = 0.85f

        /** ...and only switch to one that is within ~30 degrees of horizontal. */
        private const val AXIS_SWITCH_LOW = 0.50f

        internal fun wrapAngle(angle: Float): Float {
            var result = angle
            while (result > Math.PI) result -= (Math.PI * 2).toFloat()
            while (result <= -Math.PI) result += (Math.PI * 2).toFloat()
            return result
        }
    }

    private fun pickReferenceAxis(r: FloatArray): Int = pickReferenceAxis(r, refAxis)
}

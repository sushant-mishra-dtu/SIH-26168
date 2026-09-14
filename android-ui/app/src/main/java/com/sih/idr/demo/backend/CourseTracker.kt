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
 * Five rules do the work, in the order they fire:
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
 *  5. **Bias compensation.** What is integrated is `rate - bias`, never the raw rate (D-128).
 *     A phone gyro's null offset is a degree or two per second; nothing corrects it while GNSS is
 *     absent, so inside a tunnel it integrates straight into the course -- 1 deg/s over a 20 s
 *     bore is 20 degrees of heading, and AGENTS.md's lateral term `b_g v t^2 / 2` turns that into
 *     the traced curve leaving the bore sideways. The bias is observed in the two places it is
 *     observable and nowhere else: at a standstill, where the rate about the vertical *is* the
 *     bias (ZARU), and across a window of GNSS-tracked driving, where a persistent one-sided
 *     anchor correction is the rate the gyro is getting wrong. Neither is available inside a
 *     tunnel, which is the point: the estimate carried in at the portal is the one that runs.
 *
 * The bias here is a scalar about the world vertical, not the gyro's three-axis offset vector. It
 * is the projection of that vector onto gravity, so re-attituding the phone invalidates it and the
 * ZARU at the next stop re-learns it; the InEKF carries the vector properly. A scalar is what a
 * scalar course can use, and saying so is cheaper than implying a calibration this does not do.
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

    /** Last yaw rate about the world vertical, bias removed, bearing convention, rad/s. */
    var lastYawRateRadPerSec: Float = 0f
        private set

    /**
     * Estimated gyro null offset about the world vertical, bearing convention, rad/s (D-128).
     * Subtracted from every rate before it is integrated. Positive means the gyro reads a
     * clockwise turn that is not happening.
     */
    var gyroBiasRadPerSec: Float = 0f
        private set

    /** True once a standstill or a GNSS-tracked window has actually measured [gyroBiasRadPerSec]. */
    var hasGyroBias: Boolean = false
        private set

    // World-up axis expressed in the device frame, unit length.
    private var upX = 0f
    private var upY = 0f
    private var upZ = 1f
    private var hasUp = false

    private var lastAttitudeNs = 0L
    private var disturbedUntilNs = 0L

    // The bias observation window: seconds of course actually integrated since it opened, and the
    // total the GNSS anchor has had to correct over them. Both are thrown away whenever the course
    // stops integrating or GNSS continuity breaks, so the ratio is only ever taken over a stretch
    // where the gyro was the only thing moving the course.
    private var biasWindowSec = 0f
    private var anchorCorrectionRad = 0f

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
     * A gyro sample, in the device frame, with the speed the estimator currently believes and
     * whether the motion classifier calls this a standstill.
     *
     * [stationary] is what makes rule 5's ZARU possible: the estimator owns the ZUPT decision
     * (accelerometer quiet *and* gyro quiet, held for a duration), and a vehicle that is not
     * moving and not rotating is turning at exactly zero, so whatever the gyro reads about the
     * vertical at that moment is its null offset and nothing else.
     */
    fun onGyro(
        gxRadPerSec: Float,
        gyRadPerSec: Float,
        gzRadPerSec: Float,
        dtSec: Float,
        timestampNs: Long,
        speedMps: Float,
        stationary: Boolean = false
    ): Float {
        // Rule 1. Without an attitude the only defensible reading of a single axis is the flat,
        // screen-up case, where device z is world up; the negation is the bearing convention.
        val raw = if (hasUp) {
            -(gxRadPerSec * upX + gyRadPerSec * upY + gzRadPerSec * upZ)
        } else {
            -gzRadPerSec
        }

        // Rule 3, second half: a rate no car can turn at is a hand, not a steering wheel. Measured
        // on the raw rate: it is a statement about the sensor, not about the compensated estimate.
        if (abs(raw) > IMPLAUSIBLE_TURN_RATE_RAD_PER_SEC) {
            disturbedUntilNs = timestampNs + DISTURBANCE_HOLD_NS
        }
        updateDisturbance(timestampNs)

        // Rule 5, first half (ZARU). A standstill is the one moment the answer is known, so it is
        // the one moment the bias is measured directly. Not while the phone is being handled: the
        // classifier's standstill is about the vehicle and a hand rotating the handset is not it.
        if (stationary && !isDisturbed && dtSec > 0f) {
            val w = (dtSec / ZARU_TAU_SEC).coerceIn(0f, 1f)
            setGyroBias(gyroBiasRadPerSec + (raw - gyroBiasRadPerSec) * w)
            // A standstill is not an integration window; anything accumulated before it is spent.
            closeBiasWindow()
        }

        // Rule 5, second half: what is integrated is never the raw rate.
        val rate = raw - gyroBiasRadPerSec
        lastYawRateRadPerSec = rate

        if (isDisturbed) {
            // The course is held, so the seconds do not belong to any bias window either.
            closeBiasWindow()
            return courseRad
        }

        // Rule 2. A stopped vehicle does not change course, whatever the handset is doing.
        if (speedMps < COURSE_INTEGRATION_MIN_SPEED) {
            closeBiasWindow()
            return courseRad
        }
        if (dtSec <= 0f) return courseRad

        // Rule 4.
        val clamped = rate.coerceIn(-MAX_VEHICLE_TURN_RATE_RAD_PER_SEC, MAX_VEHICLE_TURN_RATE_RAD_PER_SEC)
        courseRad = wrapAngle(courseRad + clamped * dtSec)
        biasWindowSec += dtSec
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
            closeBiasWindow()
        } else {
            val diff = wrapAngle(bearingRad - courseRad)
            val correction = GNSS_ANCHOR_GAIN * diff
            courseRad = wrapAngle(courseRad + correction)
            observeBias(correction)
        }
        if (hasDeviceAzimuth) {
            mountOffsetRad = wrapAngle(deviceAzimuthRad - courseRad)
            hasMountOffset = true
        }
    }

    /**
     * GNSS is not correcting the course right now (D-128): the estimator is dead-reckoning, or an
     * outage has just begun or ended. Idempotent, and called for every dead-reckoned sample as
     * well as at both edges of an outage.
     *
     * The bias is learned from how hard the anchor has to pull over a window the gyro alone drove
     * *and GNSS was watching*. A window that spans an outage is not that: the first bearing at the
     * portal carries the whole accumulated heading error, real turns included, so dividing it by
     * the outage would read a multipath bearing as a calibration. The window is therefore held shut
     * for the length of the bore, and the estimate that runs inside it is the one the last clean
     * stretch of driving measured -- AGENTS.md's "bias snapshot at tunnel entry", arrived at by
     * never opening a window that could overwrite it rather than by copying a value aside.
     */
    fun onGnssDenied() {
        closeBiasWindow()
    }

    /**
     * Rule 5, second half. Over a stretch where nothing but the gyro moved the course, the total
     * the anchor had to put back is the heading the gyro got wrong, and dividing by the stretch
     * gives the rate it got wrong -- which is the bias, by definition, plus whatever bearing noise
     * survived the window. A long window and a small gain are what make the second term small: a
     * 3-degree bearing error enters as [GNSS_ANCHOR_GAIN] of itself, so over [BIAS_OBSERVATION_SEC]
     * it is ~0.19 deg/s of apparent rate error and only [BIAS_LEARN_GAIN] of that is taken. Noise
     * averages out over a drive while a real one-sided offset accumulates: measured over 20 seeds
     * of a 2-minute straight run against a 1.00 deg/s offset, the estimate lands at 1.01 +/- 0.05
     * deg/s under 3-degree bearing noise and 1.01 +/- 0.14 deg/s under 8-degree (D-128).
     */
    private fun observeBias(correctionRad: Float) {
        if (biasWindowSec <= 0f) {
            // No window is open -- the course was frozen, or this is the fix at a tunnel mouth.
            // That correction is not a rate error over anything, so it is not evidence of a bias.
            anchorCorrectionRad = 0f
            return
        }
        anchorCorrectionRad += correctionRad
        if (biasWindowSec < BIAS_OBSERVATION_SEC) return
        // A positive correction means the anchor kept adding course the gyro had not turned: the
        // rate being integrated was too small, so the bias subtracted from it is too large.
        val rateError = (anchorCorrectionRad / biasWindowSec)
            .coerceIn(-MAX_GYRO_BIAS_RAD_PER_SEC, MAX_GYRO_BIAS_RAD_PER_SEC)
        setGyroBias(gyroBiasRadPerSec - BIAS_LEARN_GAIN * rateError)
        closeBiasWindow()
    }

    private fun setGyroBias(value: Float) {
        gyroBiasRadPerSec = value.coerceIn(-MAX_GYRO_BIAS_RAD_PER_SEC, MAX_GYRO_BIAS_RAD_PER_SEC)
        hasGyroBias = true
    }

    private fun closeBiasWindow() {
        biasWindowSec = 0f
        anchorCorrectionRad = 0f
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
        gyroBiasRadPerSec = 0f
        hasGyroBias = false
        biasWindowSec = 0f
        anchorCorrectionRad = 0f
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

        /**
         * 5 deg/s. A phone gyro's null offset is a degree or two; past this it is not an offset,
         * it is a broken sensor or a standstill that was not one, and clamping keeps a single bad
         * observation from steering the course for the rest of the trip.
         */
        const val MAX_GYRO_BIAS_RAD_PER_SEC = 0.09f

        /**
         * How fast the ZARU walks the bias onto the measured rate: 4 s of continuous standstill
         * closes ~63% of the gap. Slower than the 2 s the vehicle standstill needs to be declared,
         * so a traffic-light stop contributes rather than latching a single noisy sample.
         */
        const val ZARU_TAU_SEC = 4f

        /**
         * Seconds of gyro-driven course that a bias observation is taken over. Long enough that
         * GNSS bearing noise divides down; short enough that several land in an ordinary drive.
         */
        const val BIAS_OBSERVATION_SEC = 4f

        /** How much of each observed rate error is taken. ~35 s of driving closes 90% of a bias. */
        const val BIAS_LEARN_GAIN = 0.25f

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

package com.sih.idr.demo.backend

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/** What the estimator believes it is riding in. Decides whether step integration is allowed. */
enum class MotionMode { UNKNOWN, PEDESTRIAN, VEHICLE }

/** A detected footfall: how far it carried, and the cadence speed it implies. */
data class StepEvent(val strideM: Float, val cadenceSpeedMps: Float)

/**
 * ZUPT / step detection over the accelerometer (D-127).
 *
 * This is the half of the demo estimator that decides whether the vehicle is moving at all, and
 * the speedometer read whatever it decided. Three things in the old version made that reading
 * wrong in a car:
 *
 *  - **The stationary window was counted in samples, not seconds.** Twelve frames at the requested
 *    200 Hz is 60 ms. A car cruising on smooth tarmac is quiet for 60 ms constantly, so the
 *    detector declared a standstill and slammed `speedMps` to zero several times a second -- which
 *    is the flickering speedometer, and, because the dead-reckoning branch propagates along
 *    `speedMps`, also a track that stops advancing mid-corner. The window is a *duration* here,
 *    and in a vehicle it is a long one.
 *  - **The gravity baseline chased the vehicle.** `0.985 * prev + 0.015 * sample` at 200 Hz is a
 *    0.33 s time constant: sustained acceleration was absorbed into "gravity" within a third of a
 *    second and then read as zero dynamic accel. The magnitude of gravity does not change, so the
 *    tracker is there to absorb sensor bias and nothing else, and it is slow
 *    ([GRAVITY_TAU_SEC]).
 *  - **Road vibration was read as footsteps.** Nothing gated the pedestrian step model by mode, so
 *    engine and road noise past 1.2 m/s^2 queued 0.5-0.8 m strides at up to 3.8 Hz -- a fictitious
 *    ~2.5 m/s of travel, injected along the heading frozen at the last "step", which is a large
 *    part of why the traced curve was wrong. Step detection is now off in [MotionMode.VEHICLE].
 *
 * Pure Kotlin, clock injected through the sample timestamps, so the rules can be driven from a
 * JUnit test on a laptop (D-126's reason, applied to the second half of the estimator).
 */
class MotionClassifier {

    var mode: MotionMode = MotionMode.UNKNOWN
        private set

    var isStationary: Boolean = true
        private set

    /** Smoothed |‖a‖ - g|, m/s^2: how hard the phone is being shaken, direction-free. */
    var dynamicAccelMps2: Float = 0f
        private set

    /** Tracked magnitude of gravity, m/s^2. Absorbs uncalibrated accelerometer scale and bias. */
    var gravityNormMps2: Float = STANDARD_GRAVITY
        private set

    var stepCount: Int = 0
        private set

    private var lastAccelNs = 0L
    private var quietSinceNs = 0L
    private var lastStepNs = 0L
    private var lastGyroMagRadPerSec = 0f

    /**
     * Seconds of standstill veto still owed to the last measured speed, counted down by the
     * accelerometer's own `dt`.
     *
     * Deliberately not "the timestamp the speed was seen at". A fix is stamped on
     * `SystemClock.elapsedRealtime`, a sensor event on whatever base the device chose --
     * `android/.../SessionClock.kt` exists because that is `elapsedRealtimeNanos` on almost every
     * device and `uptimeNanos` on some -- and subtracting one from the other is a number with no
     * meaning. A budget has no such problem: it is only ever decremented by intervals measured on
     * one clock.
     */
    private var movingVetoSec = 0f

    /** The gyro magnitude the ZUPT test uses. A stopped vehicle is still in rotation too (ZARU). */
    fun onGyroMagnitude(magnitudeRadPerSec: Float) {
        lastGyroMagRadPerSec = magnitudeRadPerSec
    }

    /**
     * An accelerometer sample. Returns a [StepEvent] when this sample was a footfall and step
     * integration is allowed, otherwise null.
     */
    fun onAccelerometer(ax: Float, ay: Float, az: Float, timestampNs: Long): StepEvent? {
        val norm = sqrt(ax * ax + ay * ay + az * az)
        val dt = if (lastAccelNs == 0L) {
            0f
        } else {
            ((timestampNs - lastAccelNs).coerceIn(0L, MAX_DT_NS)) / 1e9f
        }
        lastAccelNs = timestampNs

        if (dt <= 0f) {
            // The first sample has no interval to filter over. Seeding the baseline from it is
            // right for an uncalibrated sensor with a scale or bias error and wrong if the app was
            // started while the vehicle was already accelerating -- that reading would be latched
            // as "gravity" and every later sample measured against it. So it is seeded only from a
            // magnitude that could plausibly *be* gravity; anything else leaves the standard value
            // in place and the 20 s tracker walks to the truth from there.
            if (abs(norm - STANDARD_GRAVITY) < GRAVITY_SEED_TOLERANCE) gravityNormMps2 = norm
            return null
        }
        if (movingVetoSec > 0f) movingVetoSec = max(0f, movingVetoSec - dt)
        gravityNormMps2 += (norm - gravityNormMps2) * (dt / GRAVITY_TAU_SEC).coerceIn(0f, 1f)
        val instant = abs(norm - gravityNormMps2)
        dynamicAccelMps2 += (instant - dynamicAccelMps2) * (dt / DYNAMIC_TAU_SEC).coerceIn(0f, 1f)

        val quiet = dynamicAccelMps2 < ZUPT_ACCEL_THRESHOLD && lastGyroMagRadPerSec < ZUPT_GYRO_THRESHOLD
        if (quiet) {
            if (quietSinceNs == 0L) quietSinceNs = timestampNs
            val holdNs = if (mode == MotionMode.VEHICLE) VEHICLE_STATIONARY_HOLD_NS else STATIONARY_HOLD_NS
            // A GNSS speed above the moving threshold vetoes the standstill outright: the
            // accelerometer cannot see a car gliding at constant speed, and the receiver can.
            if (timestampNs - quietSinceNs >= holdNs && movingVetoSec <= 0f) {
                isStationary = true
            }
        } else {
            quietSinceNs = 0L
            if (dynamicAccelMps2 > MOTION_TRIGGER_THRESHOLD) isStationary = false
        }

        if (quiet || mode == MotionMode.VEHICLE) return null
        return detectStep(abs(norm - gravityNormMps2), timestampNs)
    }

    /**
     * A speed the receiver measured. It is the one unambiguous statement about whether this is a
     * vehicle, and the only thing that can tell a car at a steady 60 km/h from a phone on a desk.
     */
    fun observeSpeed(speedMps: Float) {
        if (speedMps >= MOVING_SPEED) {
            movingVetoSec = MOVING_VETO_SEC
            isStationary = false
            quietSinceNs = 0L
        }
        if (speedMps >= VEHICLE_SPEED) {
            mode = MotionMode.VEHICLE
        } else if (mode == MotionMode.UNKNOWN && speedMps in PEDESTRIAN_SPEED_RANGE) {
            mode = MotionMode.PEDESTRIAN
        }
    }

    /** The pose has been re-anchored or the trip restarted: forget everything that was inferred. */
    fun reset() {
        mode = MotionMode.UNKNOWN
        isStationary = true
        dynamicAccelMps2 = 0f
        gravityNormMps2 = STANDARD_GRAVITY
        stepCount = 0
        lastAccelNs = 0L
        quietSinceNs = 0L
        lastStepNs = 0L
        movingVetoSec = 0f
        lastGyroMagRadPerSec = 0f
    }

    private fun detectStep(instantDynamic: Float, timestampNs: Long): StepEvent? {
        val sinceStepNs = if (lastStepNs == 0L) Long.MAX_VALUE else timestampNs - lastStepNs
        if (instantDynamic <= STEP_PEAK_THRESHOLD || sinceStepNs <= MIN_STEP_INTERVAL_NS) return null
        val hadPrevious = lastStepNs != 0L
        lastStepNs = timestampNs
        stepCount++
        isStationary = false
        // Stride length from peak energy, 0.50-0.78 m, as before.
        val strideM = (0.45f + 0.14f * instantDynamic.coerceIn(0.8f, 3.5f)).coerceIn(0.50f, 0.78f)
        // The first step of a walk has no interval to divide by; quoting one from Long.MAX_VALUE
        // clamped to the floor invented a 3 m/s sprint. Nominal cadence until there is a second.
        val cadenceSpeed = if (!hadPrevious) {
            strideM / NOMINAL_STEP_PERIOD_SEC
        } else {
            strideM / (sinceStepNs.coerceIn(MIN_STEP_INTERVAL_NS, MAX_STEP_INTERVAL_NS) / 1e9f)
        }
        return StepEvent(strideM, cadenceSpeed)
    }

    companion object {
        /**
         * Gravity's magnitude is a constant; the tracker exists to absorb an uncalibrated sensor's
         * bias, which drifts over minutes. 20 s is slow enough that a vehicle accelerating for ten
         * seconds is still read as accelerating.
         */
        const val GRAVITY_TAU_SEC = 20f

        const val STANDARD_GRAVITY = 9.80665f

        /** How far the first sample may sit from standard gravity and still seed the baseline. */
        const val GRAVITY_SEED_TOLERANCE = 1.0f

        /** Smoothing on the dynamic-acceleration energy itself. */
        const val DYNAMIC_TAU_SEC = 0.25f

        /** ZUPT needs both: the phone is not being shaken, and it is not being rotated (ZARU). */
        const val ZUPT_ACCEL_THRESHOLD = 0.30f
        const val ZUPT_GYRO_THRESHOLD = 0.12f
        const val MOTION_TRIGGER_THRESHOLD = 0.55f

        /** Continuous quiet needed to call a standstill on foot: 0.6 s. */
        const val STATIONARY_HOLD_NS = 600_000_000L

        /**
         * ...and in a vehicle, 2 s. Smooth tarmac at a constant speed is quiet for a long time,
         * and calling that a standstill is exactly the bug this constant replaces.
         */
        const val VEHICLE_STATIONARY_HOLD_NS = 2_000_000_000L

        /** How long a measured speed keeps vetoing the standstill after it was reported. */
        const val MOVING_VETO_SEC = 3f

        /** A receiver speed at or above this means moving, whatever the accelerometer thinks. */
        const val MOVING_SPEED = 1.0f

        /** 16 km/h. Nobody walks this; from here on the step model is off. */
        const val VEHICLE_SPEED = 4.5f

        /** A speed only a walk produces, used to commit to the pedestrian model. */
        val PEDESTRIAN_SPEED_RANGE = 0.6f..2.2f

        const val STEP_PEAK_THRESHOLD = 1.20f
        const val MIN_STEP_INTERVAL_NS = 260_000_000L // max 3.8 steps/s
        const val MAX_STEP_INTERVAL_NS = 1_200_000_000L
        const val NOMINAL_STEP_PERIOD_SEC = 0.6f

        private const val MAX_DT_NS = 250_000_000L
    }
}

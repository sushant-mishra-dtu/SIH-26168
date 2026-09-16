package com.sih.idr.demo.backend

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The ZUPT and step rules of D-127 -- the half of the estimator the speedometer reads.
 *
 * [a_vehicle_is_not_stationary_because_the_road_went_quiet_for_a_moment] and
 * [road_vibration_in_a_vehicle_is_not_a_footstep] are the two the field test found. Both were
 * silent: the speedometer flickered to zero and the traced track stopped advancing, and nothing
 * on screen said why.
 */
class MotionClassifierTest {

    private val g = 9.80665f
    private val hz = 200
    private val stepNs = 1_000_000_000L / hz

    /** Feed [seconds] of samples whose magnitude is `g + amplitude`, returning the end timestamp. */
    private fun feed(
        classifier: MotionClassifier,
        seconds: Float,
        amplitude: Float,
        startNs: Long,
        gyroMag: Float = 0f
    ): Long {
        var t = startNs
        var sign = 1f
        repeat((seconds * hz).toInt()) {
            t += stepNs
            classifier.onGyroMagnitude(gyroMag)
            classifier.onAccelerometer(0f, 0f, g + sign * amplitude, t)
            sign = -sign
        }
        return t
    }

    private fun quiet(classifier: MotionClassifier, seconds: Float, startNs: Long): Long =
        feed(classifier, seconds, 0f, startNs)

    // --------------------------------------------------------------------------------------
    // The standstill
    // --------------------------------------------------------------------------------------

    @Test
    fun a_vehicle_is_not_stationary_because_the_road_went_quiet_for_a_moment() {
        // The bug, stated: the old detector wanted 12 consecutive quiet frames, and at the
        // requested 200 Hz that is 60 ms. Smooth tarmac at a constant 60 km/h delivers that
        // several times a second, and each time the speedometer was zeroed.
        val classifier = MotionClassifier()
        var t = feed(classifier, 1f, 1.0f, 0L)
        classifier.observeSpeed(16f)
        assertEquals(MotionMode.VEHICLE, classifier.mode)
        assertFalse(classifier.isStationary)

        t = quiet(classifier, 0.5f, t)
        assertFalse("60 ms of smooth road is not a standstill", classifier.isStationary)
        t = quiet(classifier, 1.5f, t)
        assertFalse("nor is two seconds, while a measured speed still vetoes it", classifier.isStationary)
    }

    @Test
    fun a_vehicle_that_really_has_stopped_is_detected() {
        val classifier = MotionClassifier()
        var t = feed(classifier, 1f, 1.0f, 0L)
        classifier.observeSpeed(16f)
        // The speed veto lasts 3 s; the vehicle quiet hold is 2 s. Both have to expire.
        t = quiet(classifier, 5f, t)
        assertTrue(classifier.isStationary)
    }

    @Test
    fun on_foot_the_standstill_comes_after_the_shorter_hold() {
        val classifier = MotionClassifier()
        var t = feed(classifier, 1f, 1.5f, 0L)
        assertFalse(classifier.isStationary)
        t = quiet(classifier, 1.5f, t)
        assertTrue(classifier.isStationary)
    }

    @Test
    fun a_measured_speed_vetoes_the_standstill_outright() {
        val classifier = MotionClassifier()
        var t = quiet(classifier, 2f, 0L)
        assertTrue(classifier.isStationary)
        classifier.observeSpeed(8f)
        assertFalse("the receiver saw motion the accelerometer cannot", classifier.isStationary)
    }

    @Test
    fun the_speed_veto_does_not_depend_on_the_sensor_timebase() {
        // `SensorEvent.timestamp` is `elapsedRealtimeNanos` on most devices and `uptimeNanos` on
        // some (`android/.../SessionClock.kt` exists for exactly that), while a GNSS fix is stamped
        // on neither. So the veto is a budget counted down by the accelerometer's own dt, and the
        // same drive must classify identically however far apart the two bases sit.
        fun run(startNs: Long): Boolean {
            val classifier = MotionClassifier()
            var t = feed(classifier, 1f, 1.0f, startNs)
            classifier.observeSpeed(16f)
            t = quiet(classifier, 5f, t)
            return classifier.isStationary
        }
        assertTrue(run(0L))
        assertTrue(run(86_400_000_000_000L)) // a device up for a day
    }

    @Test
    fun rotation_alone_blocks_the_standstill() {
        // ZARU's half of the test: a moving phone that stops being shaken but keeps turning has
        // not come to rest, and the hold never completes while the gyro says so.
        val classifier = MotionClassifier()
        var t = feed(classifier, 1f, 1.5f, 0L)
        assertFalse(classifier.isStationary)
        t = feed(classifier, 3f, 0f, t, gyroMag = 0.5f)
        assertFalse(classifier.isStationary)
        // Drop the rotation and the same quiet does finish the hold.
        t = quiet(classifier, 1f, t)
        assertTrue(classifier.isStationary)
    }

    // --------------------------------------------------------------------------------------
    // The step model
    // --------------------------------------------------------------------------------------

    @Test
    fun road_vibration_in_a_vehicle_is_not_a_footstep() {
        // The bug, stated: engine and road noise past 1.2 m/s^2 was queued as 0.5-0.8 m strides at
        // up to 3.8 Hz -- around 2.5 m/s of invented travel, laid down along a stale heading, which
        // is a large part of why the traced curve was wrong.
        val classifier = MotionClassifier()
        classifier.observeSpeed(16f)
        assertEquals(MotionMode.VEHICLE, classifier.mode)

        var t = 0L
        var steps = 0
        repeat(hz * 5) {
            t += stepNs
            classifier.onGyroMagnitude(0.05f)
            if (classifier.onAccelerometer(0f, 0f, g + 2.5f, t) != null) steps++
        }
        assertEquals(0, steps)
        assertEquals(0, classifier.stepCount)
    }

    @Test
    fun walking_peaks_are_steps() {
        val classifier = MotionClassifier()
        var t = 0L
        var steps = 0
        // A 2 Hz cadence: one 2.0 m/s^2 peak every 500 ms, quiet in between.
        repeat(10) {
            t = feed(classifier, 0.4f, 0.6f, t)
            t += stepNs
            classifier.onGyroMagnitude(0.3f)
            if (classifier.onAccelerometer(0f, 0f, g + 2.0f, t) != null) steps++
            t = feed(classifier, 0.1f, 0.6f, t)
        }
        assertTrue("expected a step per cadence peak, got $steps", steps >= 8)
        assertEquals(steps, classifier.stepCount)
    }

    @Test
    fun the_first_step_of_a_walk_does_not_report_a_sprint() {
        // There is no interval before the first step. The old code divided the stride by
        // `Long.MAX_VALUE` clamped to the 250 ms floor and quoted a 3 m/s cadence for it.
        val classifier = MotionClassifier()
        var t = feed(classifier, 0.5f, 0.6f, 0L)
        t += stepNs
        classifier.onGyroMagnitude(0.3f)
        val step = classifier.onAccelerometer(0f, 0f, g + 2.0f, t)
        assertNotNull(step)
        assertTrue("first-step speed was ${step!!.cadenceSpeedMps} m/s", step.cadenceSpeedMps < 1.6f)
    }

    @Test
    fun two_steps_cannot_arrive_inside_the_cadence_floor() {
        val classifier = MotionClassifier()
        var t = feed(classifier, 0.5f, 0.6f, 0L)
        t += stepNs
        classifier.onGyroMagnitude(0.3f)
        assertNotNull(classifier.onAccelerometer(0f, 0f, g + 2.0f, t))
        t += stepNs
        classifier.onGyroMagnitude(0.3f)
        assertNull(classifier.onAccelerometer(0f, 0f, g + 2.0f, t))
    }

    // --------------------------------------------------------------------------------------
    // The gravity baseline
    // --------------------------------------------------------------------------------------

    @Test
    fun the_gravity_baseline_does_not_absorb_a_sustained_acceleration() {
        // The bug, stated: `0.985 * prev + 0.015 * sample` at 200 Hz is a 0.33 s time constant, so
        // ten seconds of pulling away was read as "gravity" and reported as zero dynamic accel.
        val classifier = MotionClassifier()
        // At rest first, so the baseline is seeded at gravity, then eight seconds of pulling away.
        var t = quiet(classifier, 2f, 0L)
        repeat(hz * 8) {
            t += stepNs
            classifier.onGyroMagnitude(0.05f)
            classifier.onAccelerometer(0f, 0f, g + 2.0f, t)
        }
        assertTrue(
            "dynamic accel collapsed to ${classifier.dynamicAccelMps2}",
            classifier.dynamicAccelMps2 > 1.2f
        )
        assertFalse(classifier.isStationary)
    }

    @Test
    fun the_gravity_baseline_still_absorbs_a_biased_sensor() {
        // It is slow, not frozen: an uncalibrated accelerometer reading 0.4 m/s^2 high must not
        // look like permanent motion.
        val classifier = MotionClassifier()
        val t = feed(classifier, 90f, 0f, 0L)
        assertEquals(g, classifier.gravityNormMps2, 0.05f)
        assertTrue(classifier.isStationary)
    }

    // --------------------------------------------------------------------------------------
    // Mode
    // --------------------------------------------------------------------------------------

    @Test
    fun a_walking_pace_never_commits_to_the_vehicle_model() {
        val classifier = MotionClassifier()
        classifier.observeSpeed(1.4f)
        assertEquals(MotionMode.PEDESTRIAN, classifier.mode)
    }

    @Test
    fun a_reset_forgets_the_mode_and_the_step_count() {
        val classifier = MotionClassifier()
        classifier.observeSpeed(16f)
        classifier.reset()
        assertEquals(MotionMode.UNKNOWN, classifier.mode)
        assertEquals(0, classifier.stepCount)
        assertTrue(classifier.isStationary)
    }
}

package com.sih.idr.demo.backend

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.sin

/**
 * The heading rules of D-127.
 *
 * Every scenario here is a phone attitude and a vehicle motion built independently of the code, so
 * the expected course is known without running it. The two the field test found are
 * [a_mounting_angle_does_not_rotate_the_track] and
 * [re_seating_the_phone_mid_drive_leaves_the_course_where_it_was]; the rest are the reasons those
 * two work.
 */
class CourseTrackerTest {

    // --------------------------------------------------------------------------------------
    // Attitudes. `R` is what `getRotationMatrixFromVector` fills: row-major, v_world(ENU) = R v_dev,
    // so the columns are the device axes in world coordinates and the third row is world up in
    // device coordinates.
    // --------------------------------------------------------------------------------------

    /** Flat on a seat, screen up, the top of the phone (device +y) pointing along [bearingRad]. */
    private fun flatPhone(bearingRad: Float): FloatArray {
        val s = sin(bearingRad)
        val c = cos(bearingRad)
        // columns: x -> (cos, -sin, 0), y -> (sin, cos, 0), z -> up
        return floatArrayOf(
            c, s, 0f,
            -s, c, 0f,
            0f, 0f, 1f
        )
    }

    /**
     * Upright in a windscreen cradle, screen facing back down the cabin, driving along
     * [bearingRad]. Device +y points at the sky -- the case where reading the azimuth off +y
     * projected onto the ground plane divides by nothing at all.
     */
    private fun uprightPhone(bearingRad: Float): FloatArray {
        val s = sin(bearingRad)
        val c = cos(bearingRad)
        // columns: x -> right of travel, y -> up, z -> backwards
        return floatArrayOf(
            c, 0f, -s,
            -s, 0f, -c,
            0f, 1f, 0f
        )
    }

    /**
     * The gyro a device at attitude [r] reads while the vehicle turns at [bearingRateRadPerSec].
     *
     * A vehicle turn is a rotation about the world vertical and nothing else. In the bearing
     * convention a right turn is *positive*, which is a *negative* right-hand rotation about up;
     * expressed in the device frame that vector is `omega_up * (world up in device coordinates)`,
     * which is the matrix's third row.
     */
    private fun gyroForTurn(r: FloatArray, bearingRateRadPerSec: Float): FloatArray {
        val omegaUp = -bearingRateRadPerSec
        return floatArrayOf(omegaUp * r[6], omegaUp * r[7], omegaUp * r[8])
    }

    private fun assertAngle(expectedRad: Float, actualRad: Float, toleranceRad: Float = 1e-3f) {
        val diff = CourseTracker.wrapAngle(expectedRad - actualRad)
        assertTrue("expected ${expectedRad}rad, got ${actualRad}rad", abs(diff) <= toleranceRad)
    }

    /** Drive [seconds] at [speedMps] turning at [bearingRateRadPerSec], phone held at [attitude]. */
    private fun drive(
        tracker: CourseTracker,
        attitude: FloatArray,
        seconds: Float,
        bearingRateRadPerSec: Float,
        speedMps: Float,
        startNs: Long = 0L,
        hz: Int = 100
    ): Long {
        val dt = 1f / hz
        val stepNs = 1_000_000_000L / hz
        val gyro = gyroForTurn(attitude, bearingRateRadPerSec)
        var t = startNs
        repeat((seconds * hz).toInt()) {
            t += stepNs
            tracker.onRotationMatrix(attitude, t)
            tracker.onGyro(gyro[0], gyro[1], gyro[2], dt, t, speedMps)
        }
        return t
    }

    // --------------------------------------------------------------------------------------
    // The turn rate is about the world vertical, at any attitude
    // --------------------------------------------------------------------------------------

    @Test
    fun a_flat_phone_turning_right_increases_the_bearing() {
        val tracker = CourseTracker()
        val attitude = flatPhone(0f)
        tracker.onRotationMatrix(attitude, 0L)
        tracker.onGnssCourse(0f, 10f) // heading north
        // 90 degrees of right turn at 30 deg/s takes 3 s.
        drive(tracker, attitude, seconds = 3f, bearingRateRadPerSec = (PI / 6).toFloat(), speedMps = 10f)
        assertAngle((PI / 2).toFloat(), tracker.courseRad, 0.02f)
    }

    @Test
    fun an_upright_cradled_phone_reads_the_same_turn_as_a_flat_one() {
        // The bug: the old code took the device-frame z rate as the turn rate. In this attitude the
        // vehicle's turn lands entirely on device y and z reads zero, so the heading never moved.
        val flat = CourseTracker()
        val flatAttitude = flatPhone(0f)
        flat.onRotationMatrix(flatAttitude, 0L)
        flat.onGnssCourse(0f, 10f)
        drive(flat, flatAttitude, 3f, (PI / 6).toFloat(), 10f)

        val upright = CourseTracker()
        val uprightAttitude = uprightPhone(0f)
        upright.onRotationMatrix(uprightAttitude, 0L)
        upright.onGnssCourse(0f, 10f)
        drive(upright, uprightAttitude, 3f, (PI / 6).toFloat(), 10f)

        assertAngle(flat.courseRad, upright.courseRad, 1e-3f)
        assertAngle((PI / 2).toFloat(), upright.courseRad, 0.02f)
    }

    @Test
    fun a_phone_lying_face_down_reads_the_same_turn_too() {
        // Face down is the flat attitude with z pointing at the ground: the projection changes sign
        // and so does the gyro reading, and the two cancel.
        val faceUp = flatPhone(0f)
        val faceDown = floatArrayOf(
            faceUp[0], faceUp[1], -faceUp[2],
            -faceUp[3], -faceUp[4], faceUp[5],
            faceUp[6], faceUp[7], -faceUp[8]
        )
        val tracker = CourseTracker()
        tracker.onRotationMatrix(faceDown, 0L)
        tracker.onGnssCourse(0f, 10f)
        drive(tracker, faceDown, 3f, (PI / 6).toFloat(), 10f)
        assertAngle((PI / 2).toFloat(), tracker.courseRad, 0.02f)
    }

    // --------------------------------------------------------------------------------------
    // The mount angle is an offset, not a heading
    // --------------------------------------------------------------------------------------

    @Test
    fun a_mounting_angle_does_not_rotate_the_track() {
        // Two phones in the same car driving due north, one pointing along the car and one 40
        // degrees off. Both must report the car's heading; only the offsets differ. Under the old
        // rule the second one's whole traced track was rotated by 40 degrees.
        val straight = CourseTracker()
        straight.onRotationMatrix(flatPhone(0f), 1_000L)
        straight.onGnssCourse(0f, 12f)

        val skewed = CourseTracker()
        val skew = (40.0 * PI / 180.0).toFloat()
        skewed.onRotationMatrix(flatPhone(skew), 1_000L)
        skewed.onGnssCourse(0f, 12f)

        assertAngle(0f, straight.courseRad)
        assertAngle(0f, skewed.courseRad)
        assertTrue(skewed.hasMountOffset)
        assertAngle(skew, skewed.mountOffsetRad, 1e-3f)
        assertAngle(0f, straight.mountOffsetRad, 1e-3f)
    }

    @Test
    fun re_seating_the_phone_mid_drive_leaves_the_course_where_it_was() {
        // Drive east, then pick the phone up, turn it over and put it back at a new angle while
        // the car keeps going straight. The course must not move; the mount offset must.
        val tracker = CourseTracker()
        val attitude = flatPhone(0f)
        tracker.onRotationMatrix(attitude, 0L)
        tracker.onGnssCourse((PI / 2).toFloat(), 12f)
        var t = drive(tracker, attitude, 2f, 0f, 12f, startNs = 0L)
        val courseBefore = tracker.courseRad
        val offsetBefore = tracker.mountOffsetRad

        // The handling itself: the phone tumbles through a large tilt and a large yaw over 0.5 s.
        val hz = 100
        val stepNs = 1_000_000_000L / hz
        repeat(50) { i ->
            t += stepNs
            val frac = i / 50f
            val pitch = frac * (PI / 2).toFloat()
            // Tilting from flat towards upright, and swinging the azimuth round by 90 degrees.
            val tumbling = tiltedPhone(bearingRad = frac * (PI / 2).toFloat(), pitchRad = pitch)
            tracker.onRotationMatrix(tumbling, t)
            // A hand turning a phone over: 3 rad/s, far past anything a car does.
            tracker.onGyro(3f, 3f, 3f, 1f / hz, t, 12f)
        }
        assertTrue("handling should have been detected", tracker.isDisturbed)
        assertAngle(courseBefore, tracker.courseRad, 0.05f)

        // It settles at the new angle; the car has still been going straight the whole time.
        val settled = tiltedPhone(bearingRad = (PI / 2).toFloat(), pitchRad = (PI / 2).toFloat())
        t = drive(tracker, settled, 2f, 0f, 12f, startNs = t)
        assertFalse(tracker.isDisturbed)
        assertAngle(courseBefore, tracker.courseRad, 0.05f)
        assertTrue(
            "the mount offset should have absorbed the re-seat",
            abs(CourseTracker.wrapAngle(tracker.mountOffsetRad - offsetBefore)) > 0.5f
        )
    }

    /** Flat phone at [bearingRad], then pitched back by [pitchRad] about its own x axis. */
    private fun tiltedPhone(bearingRad: Float, pitchRad: Float): FloatArray {
        val flat = flatPhone(bearingRad)
        val cp = cos(pitchRad)
        val sp = sin(pitchRad)
        // Device-frame rotation about x by pitch, applied on the right: R' = R * Rx(pitch).
        val rx = floatArrayOf(
            1f, 0f, 0f,
            0f, cp, -sp,
            0f, sp, cp
        )
        val out = FloatArray(9)
        for (row in 0..2) for (col in 0..2) {
            var sum = 0f
            for (k in 0..2) sum += flat[row * 3 + k] * rx[k * 3 + col]
            out[row * 3 + col] = sum
        }
        return out
    }

    // --------------------------------------------------------------------------------------
    // The freezes
    // --------------------------------------------------------------------------------------

    @Test
    fun a_parked_car_does_not_change_course_however_the_phone_is_waved() {
        val tracker = CourseTracker()
        val attitude = flatPhone(0f)
        tracker.onRotationMatrix(attitude, 0L)
        tracker.onGnssCourse(0f, 12f)
        // Stopped at a light, and the phone is turned a full quarter circle in the hand.
        drive(tracker, attitude, seconds = 3f, bearingRateRadPerSec = (PI / 6).toFloat(), speedMps = 0.1f)
        assertAngle(0f, tracker.courseRad)
    }

    @Test
    fun a_rate_no_vehicle_can_turn_at_is_not_integrated() {
        val tracker = CourseTracker()
        val attitude = flatPhone(0f)
        tracker.onRotationMatrix(attitude, 0L)
        tracker.onGnssCourse(0f, 12f)
        drive(tracker, attitude, seconds = 1f, bearingRateRadPerSec = 5f, speedMps = 12f)
        assertAngle(0f, tracker.courseRad, 0.05f)
    }

    @Test
    fun a_single_sample_spike_is_clamped_rather_than_kinking_the_track() {
        val tracker = CourseTracker()
        val attitude = flatPhone(0f)
        tracker.onRotationMatrix(attitude, 0L)
        tracker.onGnssCourse(0f, 12f)
        // Just under the implausible bar, so it is integrated -- but clamped.
        val rate = CourseTracker.IMPLAUSIBLE_TURN_RATE_RAD_PER_SEC - 0.1f
        val gyro = gyroForTurn(attitude, rate)
        tracker.onGyro(gyro[0], gyro[1], gyro[2], 0.1f, 1_000_000L, 12f)
        assertAngle(CourseTracker.MAX_VEHICLE_TURN_RATE_RAD_PER_SEC * 0.1f, tracker.courseRad, 1e-3f)
    }

    // --------------------------------------------------------------------------------------
    // The GNSS anchor
    // --------------------------------------------------------------------------------------

    @Test
    fun a_bearing_at_a_crawl_does_not_anchor_anything() {
        val tracker = CourseTracker()
        tracker.onRotationMatrix(flatPhone(0f), 0L)
        tracker.onGnssCourse((PI / 2).toFloat(), 0.5f)
        assertFalse(tracker.hasCourse)
        tracker.onGnssCourse((PI / 2).toFloat(), 5f)
        assertTrue(tracker.hasCourse)
    }

    @Test
    fun the_anchor_closes_on_the_gnss_course_rather_than_snapping_to_it() {
        val tracker = CourseTracker()
        tracker.onRotationMatrix(flatPhone(0f), 0L)
        tracker.onGnssCourse(0f, 10f)
        repeat(20) { tracker.onGnssCourse((PI / 2).toFloat(), 10f) }
        assertAngle((PI / 2).toFloat(), tracker.courseRad, 0.02f)
    }

    @Test
    fun the_anchor_takes_the_short_way_round_north() {
        val tracker = CourseTracker()
        tracker.onRotationMatrix(flatPhone(0f), 0L)
        tracker.onGnssCourse((-3.0).toFloat(), 10f)
        // 3.1 rad is 0.18 rad away going *through* pi, not 6.1 rad the other way.
        tracker.onGnssCourse(3.1f, 10f)
        val moved = CourseTracker.wrapAngle(tracker.courseRad - (-3.0f))
        assertTrue("anchor went the long way: $moved", moved < 0f)
    }

    // --------------------------------------------------------------------------------------
    // The azimuth reference
    // --------------------------------------------------------------------------------------

    @Test
    fun the_azimuth_is_read_off_an_axis_that_is_not_pointing_at_the_sky() {
        // Upright in a cradle driving north: device +y is vertical, so its ground-plane projection
        // is atan2(0, 0). The tracker must pick another axis; device x is due east.
        val r = uprightPhone(0f)
        val axis = CourseTracker.pickReferenceAxis(r, current = 1)
        assertEquals(0, axis)
        assertAngle((PI / 2).toFloat(), CourseTracker.axisAzimuth(r, axis))
    }

    @Test
    fun the_reference_axis_is_sticky_while_it_stays_usable() {
        val r = flatPhone(0f) // device y is horizontal
        assertEquals(1, CourseTracker.pickReferenceAxis(r, current = 1))
    }

    @Test
    fun switching_the_reference_axis_re_derives_the_offset_rather_than_turning_the_course() {
        val tracker = CourseTracker()
        tracker.onRotationMatrix(flatPhone(0f), 0L)
        tracker.onGnssCourse(0f, 12f)
        val before = tracker.courseRad
        // Same car, same heading, phone tipped up into the cradle: the reference axis changes.
        tracker.onRotationMatrix(uprightPhone(0f), 1_000_000_000L)
        assertAngle(before, tracker.courseRad)
        assertAngle((PI / 2).toFloat(), tracker.mountOffsetRad)
    }

    @Test
    fun wrapAngle_lands_in_the_half_open_interval() {
        assertEquals(0f, CourseTracker.wrapAngle(0f), 1e-6f)
        assertEquals(PI.toFloat(), CourseTracker.wrapAngle(PI.toFloat()), 1e-5f)
        assertEquals(PI.toFloat(), CourseTracker.wrapAngle(-PI.toFloat()), 1e-5f)
        assertEquals(0f, CourseTracker.wrapAngle((4 * PI).toFloat()), 1e-5f)
        assertEquals(-1f, CourseTracker.wrapAngle((2 * PI).toFloat() - 1f), 1e-5f)
    }

    @Test
    fun without_a_course_the_heading_is_the_phones_azimuth_and_says_so() {
        val tracker = CourseTracker()
        tracker.onRotationMatrix(flatPhone(1f), 0L)
        assertFalse(tracker.hasCourse)
        assertAngle(1f, tracker.headingRad())
        tracker.onGnssCourse(0f, 12f)
        assertTrue(tracker.hasCourse)
        assertAngle(0f, tracker.headingRad())
    }

    @Test
    fun a_reset_forgets_the_mount_and_the_course() {
        val tracker = CourseTracker()
        tracker.onRotationMatrix(flatPhone(1f), 0L)
        tracker.onGnssCourse(0.5f, 12f)
        tracker.reset()
        assertFalse(tracker.hasCourse)
        assertFalse(tracker.hasMountOffset)
        assertFalse(tracker.hasDeviceAzimuth)
        assertEquals(0f, tracker.courseRad, 1e-6f)
    }
}

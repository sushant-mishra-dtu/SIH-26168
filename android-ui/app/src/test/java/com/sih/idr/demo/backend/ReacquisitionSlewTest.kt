package com.sih.idr.demo.backend

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

/**
 * The exit-slew rule of D-128.
 *
 * The defect these are written against is visible on the 14 Sep run: the track leaves the bore,
 * runs out to a vertex in open ground and comes straight back, because the first fix that applied
 * after the outage moved the pose 40-odd metres in one step and that step was drawn. The scenarios
 * below are the two halves of the cure -- the drawn point never moves when the correction lands,
 * and the offset is gone by the time the machine calls itself reconverged -- plus the limits that
 * stop the cure from becoming its own lie.
 */
class ReacquisitionSlewTest {

    /** Run [seconds] of decay at [hz], the rate the estimator's gyro branch calls it. */
    private fun run(slew: ReacquisitionSlew, seconds: Float, hz: Int = 100) {
        repeat((seconds * hz).toInt()) { slew.decay(1f / hz) }
    }

    @Test
    fun a_fresh_slew_is_not_running() {
        val slew = ReacquisitionSlew()
        assertFalse(slew.active)
        assertEquals(0f, slew.magnitudeM, 0f)
    }

    @Test
    fun absorbing_a_correction_leaves_the_drawn_point_exactly_where_it_was() {
        val slew = ReacquisitionSlew()
        // The state jumps 30 m north and 40 m east; reported = state + offset must not move.
        val stateNorthBefore = 100f
        val stateEastBefore = 200f
        slew.absorb(30f, 40f)
        val stateNorthAfter = stateNorthBefore + 30f
        val stateEastAfter = stateEastBefore + 40f
        assertEquals(stateNorthBefore, stateNorthAfter + slew.northM, 1e-4f)
        assertEquals(stateEastBefore, stateEastAfter + slew.eastM, 1e-4f)
        assertEquals(50f, slew.magnitudeM, 1e-3f)
    }

    @Test
    fun the_offset_is_gone_inside_the_machines_reconvergence_window() {
        val slew = ReacquisitionSlew()
        slew.absorb(40f, 0f)
        // TunnelFsmConfig.reconvergeSettleMs is 2 s; SEAMLESS_RECONVERGENCE has to be a state in
        // which something reconverges, not a label on a jump that already happened.
        run(slew, 2f)
        assertTrue("offset was ${slew.magnitudeM} m after 2 s", slew.magnitudeM < 2.5f)
    }

    @Test
    fun the_offset_reaches_exactly_zero_rather_than_tailing_off_forever() {
        val slew = ReacquisitionSlew()
        slew.absorb(40f, -12f)
        run(slew, 10f)
        assertFalse(slew.active)
        assertEquals(0f, slew.northM, 0f)
        assertEquals(0f, slew.eastM, 0f)
    }

    @Test
    fun the_drawn_point_moves_smoothly_and_only_ever_towards_the_estimate() {
        val slew = ReacquisitionSlew()
        slew.absorb(45f, 0f)
        var previous = slew.northM
        var largestStep = 0f
        repeat(200) {
            slew.decay(0.01f)
            val step = slew.northM - previous
            // Monotone: the offset shrinks, so a track drawn through it never doubles back.
            assertTrue("offset grew by $step", step >= -1e-6f)
            largestStep = maxOf(largestStep, abs(step))
            previous = slew.northM
        }
        // No single 10 ms frame moves the drawn point more than a puck's width, which is the
        // difference between a bend and the vertex the field run drew.
        assertTrue("largest single frame was $largestStep m", largestStep < 1.0f)
    }

    @Test
    fun a_second_correction_adds_to_one_still_running() {
        val slew = ReacquisitionSlew()
        slew.absorb(10f, 0f)
        slew.absorb(6f, 0f)
        assertEquals(-16f, slew.northM, 1e-4f)
    }

    @Test
    fun a_correction_too_large_to_hide_is_not_hidden() {
        val slew = ReacquisitionSlew()
        // 200 m of drift is past what two seconds of bending can honestly absorb: the display
        // takes what it can and the rest is drawn as the step it is.
        slew.absorb(200f, 0f)
        assertEquals(-ReacquisitionSlew.MAX_M, slew.northM, 1e-4f)
    }

    @Test
    fun a_reset_clears_a_running_offset() {
        val slew = ReacquisitionSlew()
        slew.absorb(20f, 20f)
        slew.reset()
        assertFalse(slew.active)
    }
}

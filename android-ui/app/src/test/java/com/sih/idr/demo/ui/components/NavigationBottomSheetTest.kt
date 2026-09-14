package com.sih.idr.demo.ui.components

import com.sih.idr.demo.backend.MotionMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * The heading-provenance chip of D-127, and the gyro bias D-128 adds to it. The point of the chip
 * is that these failures were invisible on screen: a heading that was really the handset's azimuth
 * rendered identically to one that was the vehicle's course, and an uncompensated null offset
 * renders as a perfectly smooth curve that is simply in the wrong place.
 */
class NavigationBottomSheetTest {

    @Test
    fun headingSourceLabel_names_the_three_states() {
        assertEquals("course", headingSourceLabel(headingIsCourse = true, attitudeDisturbed = false))
        assertEquals("phone azimuth", headingSourceLabel(headingIsCourse = false, attitudeDisturbed = false))
        assertEquals("held", headingSourceLabel(headingIsCourse = false, attitudeDisturbed = true))
    }

    @Test
    fun a_held_course_says_so_even_when_it_is_anchored() {
        // The handling freeze is the more urgent fact: the course on screen is not being updated.
        assertEquals("held", headingSourceLabel(headingIsCourse = true, attitudeDisturbed = true))
    }

    @Test
    fun mountOffsetLabel_is_signed_whole_degrees() {
        assertEquals("mount +90°", mountOffsetLabel((Math.PI / 2).toFloat()))
        assertEquals("mount -45°", mountOffsetLabel((-Math.PI / 4).toFloat()))
        assertEquals("mount 0°", mountOffsetLabel(0f))
    }

    @Test
    fun mountOffsetLabel_shows_nothing_before_there_is_an_offset() {
        assertNull(mountOffsetLabel(null))
    }

    @Test
    fun gyroBiasLabel_is_signed_tenths_of_a_degree_per_second() {
        assertEquals("bias +1.0°/s", gyroBiasLabel((Math.PI / 180.0).toFloat()))
        assertEquals("bias -0.5°/s", gyroBiasLabel((-Math.PI / 360.0).toFloat()))
        assertEquals("bias +0.0°/s", gyroBiasLabel(0f))
    }

    @Test
    fun gyroBiasLabel_shows_nothing_before_a_standstill_or_a_window_has_measured_one() {
        assertNull(gyroBiasLabel(null))
    }

    @Test
    fun motionModeLabel_stays_silent_until_the_estimator_has_committed() {
        assertEquals("vehicle", motionModeLabel(MotionMode.VEHICLE))
        assertEquals("on foot", motionModeLabel(MotionMode.PEDESTRIAN))
        assertNull(motionModeLabel(MotionMode.UNKNOWN))
    }
}

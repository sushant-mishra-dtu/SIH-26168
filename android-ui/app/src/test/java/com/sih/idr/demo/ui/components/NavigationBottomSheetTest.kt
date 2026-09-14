package com.sih.idr.demo.ui.components

import com.sih.idr.demo.backend.MotionMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * The heading-provenance chip of D-127. The point of the chip is that the two field bugs were
 * invisible on screen: a heading that was really the handset's azimuth rendered identically to one
 * that was the vehicle's course.
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
    fun motionModeLabel_stays_silent_until_the_estimator_has_committed() {
        assertEquals("vehicle", motionModeLabel(MotionMode.VEHICLE))
        assertEquals("on foot", motionModeLabel(MotionMode.PEDESTRIAN))
        assertNull(motionModeLabel(MotionMode.UNKNOWN))
    }
}

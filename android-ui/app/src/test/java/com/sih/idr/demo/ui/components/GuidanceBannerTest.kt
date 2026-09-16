package com.sih.idr.demo.ui.components

import org.junit.Assert.assertEquals
import org.junit.Test

class GuidanceBannerTest {

    @Test
    fun headingToDirection_cardinalPoints() {
        // 0 rad -> North (0°)
        assertEquals("Heading North (0°)", headingToDirection(0f))

        // pi / 2 rad -> East (90°)
        assertEquals("Heading East (90°)", headingToDirection((Math.PI / 2.0).toFloat()))

        // pi rad -> South (180°)
        assertEquals("Heading South (180°)", headingToDirection(Math.PI.toFloat()))

        // 3 * pi / 2 rad -> West (270°)
        assertEquals("Heading West (270°)", headingToDirection((3.0 * Math.PI / 2.0).toFloat()))
    }

    @Test
    fun headingToDirection_intercardinalPoints() {
        // pi / 4 rad -> North-East (45°)
        assertEquals("Heading North-East (45°)", headingToDirection((Math.PI / 4.0).toFloat()))

        // 3 * pi / 4 rad -> South-East (135°)
        assertEquals("Heading South-East (135°)", headingToDirection((3.0 * Math.PI / 4.0).toFloat()))

        // 5 * pi / 4 rad -> South-West (225°)
        assertEquals("Heading South-West (225°)", headingToDirection((5.0 * Math.PI / 4.0).toFloat()))

        // 7 * pi / 4 rad -> North-West (315°)
        assertEquals("Heading North-West (315°)", headingToDirection((7.0 * Math.PI / 4.0).toFloat()))
    }

    @Test
    fun headingToDirection_normalisesNegativeAndWrapping() {
        // -pi / 2 rad -> West (270°)
        assertEquals("Heading West (270°)", headingToDirection((-Math.PI / 2.0).toFloat()))

        // 2 * pi rad -> North (0°)
        assertEquals("Heading North (0°)", headingToDirection((2.0 * Math.PI).toFloat()))
    }
}

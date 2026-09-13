package com.sih.idr.demo.ui.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SpeedHudTest {

    @Test
    fun speedMpsToKmh_convertsCorrectly() {
        assertEquals(0f, speedMpsToKmh(0f), 1e-4f)
        // 10 m/s = 36 km/h
        assertEquals(36f, speedMpsToKmh(10f), 1e-4f)
        // Negative clamped to 0
        assertEquals(0f, speedMpsToKmh(-5f), 1e-4f)
    }

    @Test
    fun isSpeedOverLimit_respectsNullAndThreshold() {
        // null limit never reports over limit
        assertFalse(isSpeedOverLimit(60f, null))
        assertFalse(isSpeedOverLimit(130f, null))

        // Non-null limit checks threshold
        assertFalse(isSpeedOverLimit(50f, 50))
        assertFalse(isSpeedOverLimit(49.9f, 50))
        assertTrue(isSpeedOverLimit(50.1f, 50))
        assertTrue(isSpeedOverLimit(65f, 50))
    }

    @Test
    fun speedToGaugeFraction_clampsZeroToOne() {
        assertEquals(0f, speedToGaugeFraction(0f), 1e-4f)
        assertEquals(0.5f, speedToGaugeFraction(60f), 1e-4f)
        assertEquals(1.0f, speedToGaugeFraction(120f), 1e-4f)
        assertEquals(1.0f, speedToGaugeFraction(150f), 1e-4f)
        assertEquals(0f, speedToGaugeFraction(-10f), 1e-4f)
    }

    @Test
    fun limitTickAngleDeg_calculatesCorrectAngles() {
        // At 0 km/h: 150°
        assertEquals(150f, limitTickAngleDeg(0), 1e-4f)
        // At 60 km/h (half of 120): 150° + 120° = 270° (top dead center)
        assertEquals(270f, limitTickAngleDeg(60), 1e-4f)
        // At 50 km/h: 150° + (50/120)*240° = 150° + 100° = 250°
        assertEquals(250f, limitTickAngleDeg(50), 1e-4f)
        // At 120 km/h: 150° + 240° = 390°
        assertEquals(390f, limitTickAngleDeg(120), 1e-4f)
    }
}

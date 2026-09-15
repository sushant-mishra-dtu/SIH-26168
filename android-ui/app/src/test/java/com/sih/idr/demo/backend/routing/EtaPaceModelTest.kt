package com.sih.idr.demo.backend.routing

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class EtaPaceModelTest {

    // 6.9 km with a 13 min planned duration, as in the 14 Sep demo clip.
    private val route = NavigationRoute(
        destinationName = "AIIMS",
        destinationCoord = GeoCoordinate(28.5672, 77.2100),
        distanceMeters = 6900f,
        durationSeconds = 828L,
        points = emptyList()
    )

    private fun etaMin(pace: Float) = (route.distanceMeters / pace).toLong() / 60

    @Test
    fun seedsFromPlannedAverage() {
        val m = EtaPaceModel()
        m.reset(route)
        assertEquals(6900f / 828f, m.paceMps, 1e-3f)
    }

    @Test
    fun seedsWithDefaultWhenRouteHasNoDuration() {
        val m = EtaPaceModel()
        m.reset(route.copy(durationSeconds = 0L))
        assertEquals(EtaPaceModel.DEFAULT_PACE_MPS, m.paceMps, 1e-3f)
        m.reset(null)
        assertEquals(EtaPaceModel.DEFAULT_PACE_MPS, m.paceMps, 1e-3f)
    }

    /**
     * The demo: walking at ~2 m/s with the filter speed wobbling 0..3 m/s at 30 Hz. Before the
     * fix the ETA flipped between 13 and 52 min tick to tick; now consecutive ticks must never
     * differ by more than a minute and the value must settle to an honest walking ETA.
     */
    @Test
    fun jitteryWalkingSpeedDoesNotFlickerTheEta() {
        val m = EtaPaceModel()
        m.reset(route)
        var lastMin = etaMin(m.paceMps)
        var maxJump = 0L
        var t = 0L
        var k = 0
        // 3 minutes at 30 Hz; speed cycles through the values seen on the filter dial.
        val speeds = floatArrayOf(0.6f, 0.8f, 2.2f, 1.7f, 3.1f, 1.1f, 2.5f, 0.0f, 2.8f, 1.9f)
        while (t < 180_000L) {
            m.update(speeds[k % speeds.size], t)
            val min = etaMin(m.paceMps)
            maxJump = maxOf(maxJump, abs(min - lastMin))
            lastMin = min
            t += 33L; k++
        }
        assertTrue("ETA jumped by $maxJump min between ticks", maxJump <= 1L)
        // Mean of the moving samples (>= 1 m/s) is ~2.2 m/s -> ~52 min; the pace must be there.
        assertTrue("pace ${m.paceMps} should have converged to walking", m.paceMps in 1.9f..2.6f)
    }

    @Test
    fun standingStillHoldsThePace() {
        val m = EtaPaceModel()
        m.reset(route)
        var t = 0L
        repeat(3000) { m.update(10f, t); t += 33L } // 99 s at 36 km/h
        val cruising = m.paceMps
        assertTrue(cruising > 9f)
        repeat(3000) { m.update(0f, t); t += 33L } // 99 s at a red light
        assertEquals("a stop must not drag the ETA out", cruising, m.paceMps, 1e-4f)
        // Pulling away again: the first moving sample is one 33 ms step, not a 99 s catch-up.
        m.update(3f, t)
        assertTrue("pace ${m.paceMps} should barely move on one tick", m.paceMps > cruising - 0.1f)
    }

    @Test
    fun paceNeverDropsBelowFloor() {
        val m = EtaPaceModel()
        m.reset(route.copy(durationSeconds = 100_000L)) // absurd 0.07 m/s plan
        assertEquals(EtaPaceModel.MIN_PACE_MPS, m.paceMps, 1e-4f)
        var t = 0L
        repeat(6000) { m.update(1.0f, t); t += 33L }
        assertTrue(m.paceMps >= EtaPaceModel.MIN_PACE_MPS)
    }
}

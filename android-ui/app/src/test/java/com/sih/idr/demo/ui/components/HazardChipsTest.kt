package com.sih.idr.demo.ui.components

import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.tunnel.LatLon
import com.sih.idr.demo.backend.tunnel.TunnelDef
import com.sih.idr.demo.backend.tunnel.TunnelFix
import com.sih.idr.demo.backend.tunnel.TunnelState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HazardChipsTest {

    private val sampleTunnelWithLimit = TunnelDef(
        id = "test-tunnel",
        name = "Test Tunnel",
        centreline = listOf(LatLon(28.61, 77.22), LatLon(28.62, 77.23)),
        lengthM = 1200.0,
        postedLimitKmh = 50
    )

    private val sampleTunnelNoLimit = TunnelDef(
        id = "test-tunnel-no-limit",
        name = "Test Tunnel Unlimited",
        centreline = listOf(LatLon(28.61, 77.22), LatLon(28.62, 77.23)),
        lengthM = 800.0,
        postedLimitKmh = null
    )

    @Test
    fun idleState_producesNoChips() {
        val state = TelemetryState()
        val labels = computeActiveHazardChipLabels(state)
        assertTrue(labels.isEmpty())
    }

    @Test
    fun headlights_shownInPreArmedAndTunnelActive() {
        val preArmed = TelemetryState(tunnelState = TunnelState.PRE_ARMED_ENTRY)
        assertTrue("Headlights" in computeActiveHazardChipLabels(preArmed))

        val inTunnel = TelemetryState(tunnelState = TunnelState.TUNNEL_ACTIVE_IDR)
        assertTrue("Headlights" in computeActiveHazardChipLabels(inTunnel))

        val healthy = TelemetryState(tunnelState = TunnelState.GNSS_HEALTHY)
        assertFalse("Headlights" in computeActiveHazardChipLabels(healthy))

        val exitVerif = TelemetryState(tunnelState = TunnelState.EXIT_VERIFICATION)
        assertFalse("Headlights" in computeActiveHazardChipLabels(exitVerif))
    }

    @Test
    fun limitChip_shownOnlyWhenInsideAndPostedLimitDeclared() {
        val insideWithLimit = TelemetryState(
            tunnelFix = TunnelFix(
                tunnel = sampleTunnelWithLimit,
                alongM = 200.0,
                remainingM = 1000.0,
                lateralM = 2.0,
                distanceToEntryM = 0.0,
                inside = true
            )
        )
        assertEquals(listOf("Limit 50 km/h"), computeActiveHazardChipLabels(insideWithLimit))

        // Outside the tunnel -> no limit chip
        val outsideWithLimit = TelemetryState(
            tunnelFix = TunnelFix(
                tunnel = sampleTunnelWithLimit,
                alongM = -50.0,
                remainingM = 1250.0,
                lateralM = 2.0,
                distanceToEntryM = 50.0,
                inside = false
            )
        )
        assertFalse(computeActiveHazardChipLabels(outsideWithLimit).any { it.startsWith("Limit") })

        // Inside but limit is null -> no limit chip
        val insideNoLimit = TelemetryState(
            tunnelFix = TunnelFix(
                tunnel = sampleTunnelNoLimit,
                alongM = 200.0,
                remainingM = 600.0,
                lateralM = 2.0,
                distanceToEntryM = 0.0,
                inside = true
            )
        )
        assertFalse(computeActiveHazardChipLabels(insideNoLimit).any { it.startsWith("Limit") })
    }

    @Test
    fun gnssSuppressed_shownWhenTunnelModeActive() {
        val suppressed = TelemetryState(tunnelModeActive = true)
        assertTrue("GNSS suppressed" in computeActiveHazardChipLabels(suppressed))

        val notSuppressed = TelemetryState(tunnelModeActive = false)
        assertFalse("GNSS suppressed" in computeActiveHazardChipLabels(notSuppressed))
    }

    @Test
    fun forced_shownWhenTunnelForced() {
        val forced = TelemetryState(tunnelForced = true)
        assertTrue("Forced" in computeActiveHazardChipLabels(forced))

        val notForced = TelemetryState(tunnelForced = false)
        assertFalse("Forced" in computeActiveHazardChipLabels(notForced))
    }

    @Test
    fun lowLight_shownWhenLuxBelowThreshold() {
        val dark = TelemetryState(ambientLux = 25f)
        assertTrue("Low light" in computeActiveHazardChipLabels(dark))

        val borderline = TelemetryState(ambientLux = 49.9f)
        assertTrue("Low light" in computeActiveHazardChipLabels(borderline))

        val bright = TelemetryState(ambientLux = 55f)
        assertFalse("Low light" in computeActiveHazardChipLabels(bright))

        val unknown = TelemetryState(ambientLux = null)
        assertFalse("Low light" in computeActiveHazardChipLabels(unknown))
    }

    @Test
    fun multipleHazardChips_combineInClosedSet() {
        val multiState = TelemetryState(
            tunnelState = TunnelState.TUNNEL_ACTIVE_IDR,
            tunnelModeActive = true,
            tunnelForced = true,
            ambientLux = 15f,
            tunnelFix = TunnelFix(
                tunnel = sampleTunnelWithLimit,
                alongM = 300.0,
                remainingM = 900.0,
                lateralM = 1.5,
                distanceToEntryM = 0.0,
                inside = true
            )
        )
        val expected = listOf("Headlights", "Limit 50 km/h", "GNSS suppressed", "Forced", "Low light")
        assertEquals(expected, computeActiveHazardChipLabels(multiState))
    }
}

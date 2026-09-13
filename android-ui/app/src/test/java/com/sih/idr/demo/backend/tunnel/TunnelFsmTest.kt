package com.sih.idr.demo.backend.tunnel

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The tunnel machine, driven by scripted signals on an injected clock. Each test is one scenario
 * from `docs/TUNNEL_MODE_AND_NAVIGATION_UPGRADES.md` section 1 or one of the four documented
 * deviations from its diagram (see the class comment on [TunnelFsm]), so a failure names the
 * behaviour that changed rather than a line that broke.
 */
class TunnelFsmTest {

    private val config = TunnelFsmConfig()

    /** A receiver under a clear sky: one fix per second, strong C/N0, many satellites. */
    private fun TunnelFsm.healthySecond(t: Long) {
        onGnssStatus(t, satellitesUsed = 12, cn0Top4DbHz = 42f)
        onGnssFix(t, FixVerdict.ACCEPTED)
    }

    private fun TunnelFsm.driveHealthy(fromMs: Long, toMs: Long) {
        var t = fromMs
        while (t <= toMs) {
            healthySecond(t)
            t += 1_000
        }
    }

    private fun TunnelFsm.lastTrigger(): TunnelTrigger? = lastTransition?.trigger

    // ── Healthy ──────────────────────────────────────────────────────────────────────────

    @Test
    fun startsHealthyAndStaysThereUnderAClearSky() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 30_000)
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        assertTrue(fsm.transitions.isEmpty())
    }

    @Test
    fun aLateFixUnderAClearSkyIsNotATunnel() {
        // Deviation 4: 1 Hz receivers jitter past 1.2 s on ordinary days.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 5_000)
        fsm.tick(6_500) // 1.5 s since the last fix, C/N0 still strong
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        fsm.healthySecond(6_600)
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
    }

    @Test
    fun aReceiverThatNeverFixesTimesOutIntoDeadReckoning() {
        // The desk case: the app starts indoors and no fix ever arrives.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.tick(1_000)
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        fsm.tick(1_300)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.GNSS_TIMEOUT, fsm.lastTrigger())
    }

    // ── Entry ────────────────────────────────────────────────────────────────────────────

    @Test
    fun cn0CollapseThenSilenceIsTheDocumentsEntryPath() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        // C/N0 drops sharply: pre-arm.
        fsm.onGnssStatus(10_400, satellitesUsed = 3, cn0Top4DbHz = 20f)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        assertEquals(TunnelTrigger.CN0_COLLAPSE, fsm.lastTrigger())
        // No fix for more than 1.2 s after the last one at t = 10 s: tunnel.
        fsm.tick(11_100)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        fsm.tick(11_300)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.GNSS_TIMEOUT, fsm.lastTrigger())
        assertTrue(fsm.state.suppressesGnss)
    }

    @Test
    fun cn0BelowTheLostThresholdConfirmsEntryWithoutWaitingForTheTimeout() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onGnssStatus(10_300, satellitesUsed = 2, cn0Top4DbHz = 22f)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        fsm.onGnssStatus(10_600, satellitesUsed = 0, cn0Top4DbHz = 12f)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.CN0_LOST, fsm.lastTrigger())
    }

    @Test
    fun aFootbridgeDipRecoversWithoutEverEnteringTunnelMode() {
        // Deviation 1: the reverse edge out of PRE_ARMED_ENTRY.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onGnssStatus(10_500, satellitesUsed = 5, cn0Top4DbHz = 21f) // dip
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        // Fixes keep coming and C/N0 is back within a second.
        fsm.onGnssFix(11_000, FixVerdict.ACCEPTED)
        fsm.onGnssStatus(11_000, satellitesUsed = 12, cn0Top4DbHz = 40f)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        fsm.healthySecond(12_000)
        fsm.healthySecond(13_000)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state) // not yet 3 s healthy
        fsm.healthySecond(14_000)
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        assertEquals(TunnelTrigger.PRE_ARM_CLEARED, fsm.lastTrigger())
        assertFalse(fsm.transitions.any { it.to == TunnelState.TUNNEL_ACTIVE_IDR })
    }

    @Test
    fun aRelapseDuringTheClearWindowRestartsIt() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onGnssStatus(10_500, satellitesUsed = 5, cn0Top4DbHz = 21f)
        fsm.healthySecond(11_000)
        fsm.healthySecond(12_000)
        fsm.onGnssStatus(12_500, satellitesUsed = 5, cn0Top4DbHz = 22f) // dips again
        fsm.healthySecond(13_000)
        fsm.healthySecond(14_000)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        fsm.healthySecond(15_000)
        fsm.healthySecond(16_000)
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
    }

    @Test
    fun theMappedPortalPreArmsAtFortyMetresAndEntersAtZero() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onPortalDistance(10_100, 90f)
        assertTrue(fsm.hazardZone) // Stage 2 banner distance, no state change
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        fsm.onPortalDistance(10_200, 35f)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        assertEquals(TunnelTrigger.PORTAL_NEAR, fsm.lastTrigger())
        fsm.onPortalDistance(10_300, -2f)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.PORTAL_PASSED, fsm.lastTrigger())
    }

    @Test
    fun theMapSayingInTunnelIsAnEntryTriggerOnItsOwn() {
        // Section 7.5: a fourth entry trigger, map-data based.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onMapInTunnel(10_100, true)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.MAP_IN_TUNNEL, fsm.lastTrigger())
    }

    @Test
    fun theMapSayingInTunnelIsNotAnExitTrigger() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onMapInTunnel(10_100, true)
        fsm.onMapInTunnel(20_000, false)
        fsm.tick(21_000)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
    }

    @Test
    fun aLuxDropAlonePreArmsButDoesNotEnter() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onLight(9_900, 30_000f)
        fsm.onLight(10_100, 20_000f) // -50,000 lux/s: a cloud edge, or a portal
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        assertEquals(TunnelTrigger.LUX_DROP, fsm.lastTrigger())
        fsm.healthySecond(11_000)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        assertFalse(fsm.state.suppressesGnss)
    }

    @Test
    fun aLuxDropCoincidingWithCn0CollapseConfirmsEntry() {
        // Section 1.1.C: optical confirmation.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onLight(9_900, 30_000f)
        // A suspect-grade drop: on its own this only pre-arms, and would need the 1.2 s
        // timeout or a lost-grade report to enter.
        fsm.onGnssStatus(10_200, satellitesUsed = 3, cn0Top4DbHz = 21f)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        // The portal's shadow, 200 ms later: entry now, not at the timeout.
        fsm.onLight(10_400, 80f)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.LUX_DROP, fsm.lastTrigger())
    }

    @Test
    fun aReportTrackingNoSatellitesIsACollapse() {
        // Section 1.1.A: used-in-fix 12+ -> 0. No C/N0 at all is not "no data", it is no signal.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onGnssStatus(10_400, satellitesUsed = 0, cn0Top4DbHz = null)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.CN0_LOST, fsm.lastTrigger())
    }

    @Test
    fun aStaleHealthyReportCannotMaskALoss() {
        // Deviation 4: the last GnssStatus said 42 dB-Hz, then the callback stopped with the fixes.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.tick(12_000) // 2 s silent, status 2 s old: still "healthy" -> no timeout yet
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        fsm.tick(13_100) // status now older than statusFreshMs
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.GNSS_TIMEOUT, fsm.lastTrigger())
    }

    @Test
    fun aMappedEntryIsNotUndoneByTheStaleHealthyReportBeforeIt() {
        // Deviation 5: the portal fires before the receiver notices.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000) // last status: 42 dB-Hz, 12 used
        fsm.onPortalDistance(10_300, -1f)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        fsm.tick(10_600)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        // A report made after entry that says the sky is back does count.
        fsm.onGnssStatus(11_000, satellitesUsed = 8, cn0Top4DbHz = 36f)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
    }

    @Test
    fun aSpentMapEdgeCannotReEnterAfterAVerifiedExit() {
        // Deviation 5: inTunnel stays true for the whole bore; only a new edge re-enters.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onMapInTunnel(10_100, true)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        fsm.onGnssFix(60_000, FixVerdict.ACCEPTED)
        fsm.onGnssFix(61_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.SEAMLESS_RECONVERGENCE, fsm.state)
        fsm.onGnssStatus(61_500, satellitesUsed = 9, cn0Top4DbHz = 38f)
        fsm.healthySecond(62_000)
        fsm.healthySecond(63_000)
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        fsm.healthySecond(64_000) // map still says true; no new edge
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        fsm.onMapInTunnel(65_000, false)
        fsm.onMapInTunnel(66_000, true) // the next bore
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
    }

    @Test
    fun aBrightToDarkStepBetweenSparseReadingsCountsAsADrop() {
        // Light sensors report on change; a dashboard-mounted phone may go minutes between
        // readings, so a raw derivative would miss the portal.
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onLight(8_000, 25_000f)
        fsm.onLight(10_500, 100f) // 2.5 s apart: -9,960 lux/s, and bright-to-dark
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
    }

    @Test
    fun aSlowDimmingIsNotADrop() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onLight(0, 25_000f)
        fsm.onLight(10_000, 100f) // 10 s apart: dusk, not a portal
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
    }

    @Test
    fun theBarometricPistonPreArms() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        var t = 9_000L
        while (t <= 10_000) {
            fsm.onPressure(t, 1_005.00f)
            t += 40
        }
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        fsm.onPressure(10_040, 1_005.15f)
        fsm.onPressure(10_080, 1_005.30f)
        fsm.onPressure(10_120, 1_005.45f) // +0.45 hPa in 120 ms
        assertEquals(TunnelState.PRE_ARMED_ENTRY, fsm.state)
        assertEquals(TunnelTrigger.BARO_PISTON, fsm.lastTrigger())
    }

    @Test
    fun aSlowPressureTrendIsNotAPiston() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        var t = 0L
        var hPa = 1_000f
        while (t <= 10_000) {
            fsm.onPressure(t, hPa)
            hPa += 0.02f // +5 hPa over 10 s: a descent, not a portal
            t += 40
        }
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
    }

    // ── Exit ─────────────────────────────────────────────────────────────────────────────

    /** The document's own entry path: a suspect C/N0 report, then 1.2 s without a fix. */
    private fun enteredTunnel(): TunnelFsm {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 10_000)
        fsm.onGnssStatus(10_400, satellitesUsed = 3, cn0Top4DbHz = 20f)
        fsm.tick(11_300)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        return fsm
    }

    @Test
    fun twoConsecutivePassesReconvergeAndThenSettleToHealthy() {
        val fsm = enteredTunnel()
        fsm.onGnssFix(60_000, FixVerdict.REJECTED) // first fix at the portal: multipath
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
        assertEquals(TunnelTrigger.FIX_REAPPEARED, fsm.transitions[fsm.transitions.size - 1].trigger)
        assertTrue(fsm.state.suppressesGnss)
        fsm.onGnssFix(61_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
        fsm.onGnssFix(62_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.SEAMLESS_RECONVERGENCE, fsm.state)
        assertEquals(TunnelTrigger.CHI2_PASS, fsm.lastTrigger())
        assertFalse(fsm.state.suppressesGnss)
        fsm.onGnssStatus(62_500, satellitesUsed = 9, cn0Top4DbHz = 38f)
        fsm.onGnssFix(63_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.SEAMLESS_RECONVERGENCE, fsm.state)
        fsm.onGnssFix(64_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.GNSS_HEALTHY, fsm.state)
        assertEquals(TunnelTrigger.RECONVERGED, fsm.lastTrigger())
    }

    @Test
    fun aRejectedFixResetsThePassCounterInsteadOfBouncingTheState() {
        // Deviation 2.
        val fsm = enteredTunnel()
        fsm.onGnssFix(60_000, FixVerdict.ACCEPTED)
        assertEquals(1, fsm.consecutivePasses)
        fsm.onGnssFix(61_000, FixVerdict.REJECTED)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
        assertEquals(0, fsm.consecutivePasses)
        fsm.onGnssFix(62_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
        fsm.onGnssFix(63_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.SEAMLESS_RECONVERGENCE, fsm.state)
        assertEquals(1, fsm.transitions.count { it.to == TunnelState.EXIT_VERIFICATION })
    }

    @Test
    fun aForcedAcceptanceReconvergesUnderItsOwnName() {
        // Deviation 3: never recorded as a pass.
        val fsm = enteredTunnel()
        fsm.onGnssFix(60_000, FixVerdict.REJECTED)
        fsm.onGnssFix(61_000, FixVerdict.REJECTED)
        fsm.onGnssFix(62_000, FixVerdict.FORCED)
        assertEquals(TunnelState.SEAMLESS_RECONVERGENCE, fsm.state)
        assertEquals(TunnelTrigger.CHI2_FORCED, fsm.lastTrigger())
        assertFalse(fsm.transitions.any { it.trigger == TunnelTrigger.CHI2_PASS })
    }

    @Test
    fun losingTheSignalAgainDuringVerificationFallsBackToDeadReckoning() {
        // A gap between two bores.
        val fsm = enteredTunnel()
        fsm.onGnssFix(60_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
        fsm.tick(61_300)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.GNSS_TIMEOUT, fsm.lastTrigger())
        // And the pass counter starts over on the next exit.
        fsm.onGnssFix(70_000, FixVerdict.ACCEPTED)
        assertEquals(1, fsm.consecutivePasses)
    }

    @Test
    fun losingTheSignalDuringReconvergenceFallsBackToo() {
        val fsm = enteredTunnel()
        fsm.onGnssFix(60_000, FixVerdict.ACCEPTED)
        fsm.onGnssFix(61_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.SEAMLESS_RECONVERGENCE, fsm.state)
        fsm.tick(62_300)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
    }

    @Test
    fun cn0RecoveryWithoutAFixYetStartsVerification() {
        // Section 1.2: "satellites reappear: C/N0 > 24".
        val fsm = enteredTunnel()
        fsm.onGnssStatus(60_000, satellitesUsed = 6, cn0Top4DbHz = 30f)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
        assertEquals(TunnelTrigger.CN0_RECOVERED, fsm.lastTrigger())
    }

    @Test
    fun cn0RecoveryNeedsEnoughSatellitesUsed() {
        val fsm = enteredTunnel()
        fsm.onGnssStatus(60_000, satellitesUsed = 2, cn0Top4DbHz = 30f)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
    }

    // ── Manual override ──────────────────────────────────────────────────────────────────

    @Test
    fun forcingPinsTheMachineInTunnelModeWhateverTheSignalsSay() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 5_000)
        fsm.setForced(5_100, true)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertEquals(TunnelTrigger.MANUAL_ON, fsm.lastTrigger())
        fsm.driveHealthy(6_000, 20_000)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertTrue(fsm.forced)
    }

    @Test
    fun releasingTheOverrideWithFixesFlowingRunsTheExitPath() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 5_000)
        fsm.setForced(5_100, true)
        fsm.driveHealthy(6_000, 10_000)
        fsm.setForced(10_200, false)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
        assertEquals(TunnelTrigger.MANUAL_OFF, fsm.lastTrigger())
        fsm.onGnssFix(11_000, FixVerdict.ACCEPTED)
        fsm.onGnssFix(12_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.SEAMLESS_RECONVERGENCE, fsm.state)
    }

    @Test
    fun releasingTheOverrideWithNoFixesLeavesTheSignalsToDecide() {
        val fsm = TunnelFsm(config, startMs = 0)
        fsm.driveHealthy(0, 5_000)
        fsm.setForced(5_100, true)
        fsm.setForced(30_000, false) // 25 s without a fix
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, fsm.state)
        assertFalse(fsm.forced)
        fsm.onGnssFix(31_000, FixVerdict.ACCEPTED)
        assertEquals(TunnelState.EXIT_VERIFICATION, fsm.state)
    }

    // ── Bookkeeping ──────────────────────────────────────────────────────────────────────

    @Test
    fun transitionsAreLoggedInOrderWithTheirTriggerAndTime() {
        val fsm = enteredTunnel()
        val log = fsm.transitions
        assertEquals(2, log.size)
        assertEquals(TunnelState.GNSS_HEALTHY, log[0].from)
        assertEquals(TunnelState.PRE_ARMED_ENTRY, log[0].to)
        assertEquals(TunnelTrigger.CN0_COLLAPSE, log[0].trigger)
        assertEquals(10_400L, log[0].atMs)
        assertEquals(TunnelState.TUNNEL_ACTIVE_IDR, log[1].to)
        assertEquals(TunnelTrigger.GNSS_TIMEOUT, log[1].trigger)
        assertEquals(11_300L, log[1].atMs)
    }

    @Test
    fun theTransitionLogIsBounded() {
        val fsm = TunnelFsm(config.copy(historySize = 4), startMs = 0)
        var t = 0L
        repeat(5) {
            fsm.setForced(t, true)
            t += 100
            fsm.onGnssFix(t, FixVerdict.ACCEPTED)
            fsm.setForced(t, false)
            t += 100
        }
        assertEquals(4, fsm.transitions.size)
    }

    @Test
    fun nothingIsReportedBeforeTheSensorsReport() {
        val fsm = TunnelFsm(config, startMs = 0)
        assertNull(fsm.cn0Top4DbHz)
        assertNull(fsm.lux)
        assertNull(fsm.portalDistanceM)
        assertNull(fsm.mapInTunnel)
        assertFalse(fsm.hazardZone)
    }
}

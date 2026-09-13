package com.sih.idr.demo.backend.tunnel

/**
 * The autonomous tunnel state machine of `docs/TUNNEL_MODE_AND_NAVIGATION_UPGRADES.md` section 1.2,
 * with the corrections of `docs/UI_UX_NAVIGATION_PLAN.md` section 7.5 (D-126).
 *
 * Pure Kotlin, no Android imports, time injected as `nowMs` (the caller passes
 * `SystemClock.elapsedRealtime()`), so every transition is reproducible from a list of signal
 * events and is unit tested in `app/src/test`. Nothing here computes a position: the machine
 * decides *when* the estimator suppresses GNSS and *when* a fix has been verified; the estimator
 * owns the chi-square gate and reports its verdict back through [onGnssFix].
 *
 * Where this deliberately departs from the diagram, and why:
 *
 * 1. **A reverse edge `PRE_ARMED_ENTRY -> GNSS_HEALTHY`.** The document's stated goal is to avoid
 *    false positives under a footbridge or a tree canopy; a pre-arm that can only proceed to
 *    tunnel mode cannot meet it. Pre-arming is cheap (a bias snapshot), so it is entered eagerly
 *    and cleared once every signal has been healthy for [TunnelFsmConfig.preArmClearMs].
 * 2. **A rejected fix in `EXIT_VERIFICATION` resets the pass counter instead of returning to
 *    `TUNNEL_ACTIVE_IDR`.** The diagram's loop-back edge, taken literally, flips the status pill
 *    at 1 Hz on every multipath fix at a portal. The state falls back only when the signal is
 *    lost again ([TunnelFsmConfig.gnssTimeoutMs]) -- a gap between two bores.
 * 3. **A forced acceptance is a distinct trigger.** The estimator applies D-115's anti-lockout
 *    rule (a fix rejected N times running is applied); the machine records that as
 *    [TunnelTrigger.CHI2_FORCED], never as a pass, so the exit summary cannot claim a
 *    verification that did not happen.
 * 4. **The timeout out of `GNSS_HEALTHY` also needs C/N0 to be unhealthy, unknown or stale.** A
 *    1 Hz fix that arrives 1.3 s late under a clear sky is not a tunnel; without this the machine
 *    would flap on ordinary receiver jitter. "Healthy" needs a report younger than
 *    [TunnelFsmConfig.statusFreshMs], so a receiver that stops reporting cannot mask a loss.
 * 5. **Map inputs are edge-triggered.** `inTunnel` stays true and `distanceToStart` stays
 *    negative for the whole bore; taken as levels they would re-enter tunnel mode one second
 *    after every GNSS-verified exit. Only a fresh edge -- one that happened after the last exit
 *    -- can trigger entry, and a C/N0 recovery counts only if it was reported after entry, so
 *    the stale "healthy" report from just before a mapped portal cannot bounce the machine out.
 *
 * Two inputs the document lists are absent on purpose. HDOP is not exposed by `GnssStatus`
 * (it is an NMEA field), so it is not a trigger. `GnssMeasurementsEvent` cadence on the team
 * phone is unmeasured (section 7.5), so no sub-second latency is claimed anywhere: the
 * sub-second path is the portal distance and the lux derivative, and C/N0 confirms.
 *
 * The map-side inputs ([onPortalDistance], [onMapInTunnel]) are fed by nothing until the
 * `mapbox` flavour runs a trip session; they are null and inert until then.
 */
enum class TunnelState(val label: String, val suppressesGnss: Boolean) {
    /** Fixes flow and are applied. */
    GNSS_HEALTHY("GNSS lock", suppressesGnss = false),

    /** Something says a portal is near. The filter snapshots its gyro bias; fixes still apply. */
    PRE_ARMED_ENTRY("Pre-arming IDR", suppressesGnss = false),

    /** No usable GNSS. Dead reckoning drives the pose; fixes are gated and not applied. */
    TUNNEL_ACTIVE_IDR("IDR · GNSS denied", suppressesGnss = true),

    /** Fixes are back and being gated; none is applied until enough pass in a row. */
    EXIT_VERIFICATION("Verifying GPS fix", suppressesGnss = true),

    /** Verified fixes are blended in over a short window; then healthy. */
    SEAMLESS_RECONVERGENCE("GPS restored", suppressesGnss = false),
}

/** What caused a transition. Logged with every one, so a demo can be audited afterwards (D-080). */
enum class TunnelTrigger {
    CN0_COLLAPSE,
    CN0_LOST,
    CN0_RECOVERED,
    PORTAL_NEAR,
    PORTAL_PASSED,
    MAP_IN_TUNNEL,
    LUX_DROP,
    BARO_PISTON,
    GNSS_TIMEOUT,
    PRE_ARM_CLEARED,
    FIX_REAPPEARED,
    CHI2_PASS,
    CHI2_FORCED,
    RECONVERGED,
    MANUAL_ON,
    MANUAL_OFF,
}

/** The estimator's verdict on one GNSS fix, reported to the machine. */
enum class FixVerdict {
    /** Innovation inside the chi-square gate. */
    ACCEPTED,

    /** Outside the gate: treated as a multipath artefact and not applied. */
    REJECTED,

    /** Outside the gate but applied anyway under the anti-lockout rule (D-115). Not a pass. */
    FORCED,
}

data class TunnelTransition(
    val from: TunnelState,
    val to: TunnelState,
    val trigger: TunnelTrigger,
    val atMs: Long,
)

/**
 * Thresholds, with the document's numbers as defaults. None of them has been measured on the
 * team phone; the D-116 way -- record, then set -- applies before any of them is quoted.
 */
data class TunnelFsmConfig(
    /** Section 1.2 table: healthy means C/N0 above this with at least [minSatsHealthy] used. */
    val cn0HealthyDbHz: Float = 28f,
    /** Below this the receiver is suspect (pre-arm); above it at an exit, satellites are back. */
    val cn0SuspectDbHz: Float = 24f,
    /** Section 1.1.A: below this the signal has collapsed. */
    val cn0LostDbHz: Float = 18f,
    val minSatsHealthy: Int = 4,
    /** Section 1.1.B: pre-arm inside this distance to the portal. */
    val portalPreArmM: Float = 40f,
    /** Plan section 2, Stage 2: the hazard banner is raised inside this distance. */
    val portalHazardM: Float = 100f,
    /** Section 1.2: no fix for longer than this is signal loss. */
    val gnssTimeoutMs: Long = 1_200L,
    /** A `GnssStatus` report older than this no longer counts as evidence of health (deviation 4). */
    val statusFreshMs: Long = 3_000L,
    /** Section 1.1.C: a lux derivative steeper than this (negative) is a portal. */
    val luxDropRatePerS: Float = -5_000f,
    /** A drop from above [luxBright] to below [luxTunnel] between two readings also counts ... */
    val luxBright: Float = 1_000f,
    val luxTunnel: Float = 150f,
    /** ... provided the two readings are no further apart than this (light sensors report on change). */
    val luxReadingGapMs: Long = 3_000L,
    /**
     * How long a lux drop or a baro piston is remembered as "just happened". Section 1.1.C: a
     * lux drop confirms entry only if C/N0 collapsed within this same window.
     */
    val transientWindowMs: Long = 2_000L,
    /** Section 1.1.D: a rise of at least this over [baroWindowMs] is the piston transient. */
    val baroPistonHpa: Float = 0.3f,
    val baroWindowMs: Long = 200L,
    /** How long every signal must read healthy before a pre-arm is cleared (deviation 1). */
    val preArmClearMs: Long = 3_000L,
    /** Section 1.2: consecutive gate passes needed before fixes are applied again. */
    val consecutivePassesToReconverge: Int = 2,
    /** Section 3.5: the blend window, after which the machine is healthy again. */
    val reconvergeSettleMs: Long = 2_000L,
    /** Transitions kept for the log. */
    val historySize: Int = 64,
)

class TunnelFsm(
    private val config: TunnelFsmConfig = TunnelFsmConfig(),
    startMs: Long = 0L,
) {
    var state: TunnelState = TunnelState.GNSS_HEALTHY
        private set

    private val history = ArrayDeque<TunnelTransition>()

    /** Every transition so far, oldest first, bounded to [TunnelFsmConfig.historySize]. */
    val transitions: List<TunnelTransition> get() = history.toList()
    val lastTransition: TunnelTransition? get() = history.lastOrNull()

    /** The manual override. While set, the machine sits in `TUNNEL_ACTIVE_IDR` whatever the signals. */
    var forced: Boolean = false
        private set

    // ── Signals, as last reported ────────────────────────────────────────────────────────
    /** The start counts as the last fix: a receiver that never fixes times out like a lost one. */
    private var lastFixMs: Long = startMs
    private var stateEnteredMs: Long = startMs
    var cn0Top4DbHz: Float? = null
        private set
    var satellitesUsed: Int = 0
        private set
    private var statusAtMs: Long = Long.MIN_VALUE
    private var cn0DroppedAtMs: Long = Long.MIN_VALUE
    var lux: Float? = null
        private set
    private var luxAtMs: Long = Long.MIN_VALUE
    private var luxDropAtMs: Long = Long.MIN_VALUE
    private val baro = ArrayDeque<Pair<Long, Float>>()
    private var baroPistonAtMs: Long = Long.MIN_VALUE
    var portalDistanceM: Float? = null
        private set
    private var portalPassedAtMs: Long = Long.MIN_VALUE
    var mapInTunnel: Boolean? = null
        private set
    private var mapInTunnelAtMs: Long = Long.MIN_VALUE
    /** When the machine last left a GNSS-suppressing state; map edges older than this are spent. */
    private var lastExitMs: Long = Long.MIN_VALUE
    private var preArmHealthySinceMs: Long = Long.MIN_VALUE

    /** Passes counted in `EXIT_VERIFICATION` since the last rejection. */
    var consecutivePasses: Int = 0
        private set

    /** Plan section 2, Stage 2: inside the hazard-banner distance of a mapped portal. */
    val hazardZone: Boolean
        get() = portalDistanceM?.let { it >= 0f && it < config.portalHazardM } == true

    // ── Inputs ───────────────────────────────────────────────────────────────────────────

    /** From `GnssStatus.Callback`: satellites used in the fix and the mean C/N0 of the best four. */
    fun onGnssStatus(nowMs: Long, satellitesUsed: Int, cn0Top4DbHz: Float?) {
        this.satellitesUsed = satellitesUsed
        this.cn0Top4DbHz = cn0Top4DbHz
        statusAtMs = nowMs
        // A report with no tracked satellites at all is a collapse, not an absence of data.
        if (cn0Top4DbHz == null || cn0Top4DbHz < config.cn0SuspectDbHz) cn0DroppedAtMs = nowMs
        evaluate(nowMs)
    }

    /** Every GNSS fix, with the estimator's verdict on it. The fix itself never enters here. */
    fun onGnssFix(nowMs: Long, verdict: FixVerdict) {
        lastFixMs = nowMs
        if (!forced && state == TunnelState.TUNNEL_ACTIVE_IDR) {
            transition(TunnelState.EXIT_VERIFICATION, TunnelTrigger.FIX_REAPPEARED, nowMs)
        }
        if (!forced && state == TunnelState.EXIT_VERIFICATION) {
            when (verdict) {
                FixVerdict.ACCEPTED -> {
                    consecutivePasses++
                    if (consecutivePasses >= config.consecutivePassesToReconverge) {
                        transition(TunnelState.SEAMLESS_RECONVERGENCE, TunnelTrigger.CHI2_PASS, nowMs)
                    }
                }
                FixVerdict.FORCED -> {
                    transition(TunnelState.SEAMLESS_RECONVERGENCE, TunnelTrigger.CHI2_FORCED, nowMs)
                }
                FixVerdict.REJECTED -> consecutivePasses = 0
            }
        }
        evaluate(nowMs)
    }

    /** From `Sensor.TYPE_LIGHT`. Reports on change, so the gap between readings is unbounded. */
    fun onLight(nowMs: Long, lux: Float) {
        val previous = this.lux
        val previousAt = luxAtMs
        this.lux = lux
        luxAtMs = nowMs
        if (previous != null && previousAt != Long.MIN_VALUE) {
            val dtS = ((nowMs - previousAt).coerceAtLeast(1L)) / 1000f
            val rate = (lux - previous) / dtS
            val steep = rate < config.luxDropRatePerS
            val brightToDark = previous >= config.luxBright && lux < config.luxTunnel &&
                nowMs - previousAt <= config.luxReadingGapMs
            if (steep || brightToDark) luxDropAtMs = nowMs
        }
        evaluate(nowMs)
    }

    /** From `Sensor.TYPE_PRESSURE`, hectopascals. */
    fun onPressure(nowMs: Long, hPa: Float) {
        baro.addLast(nowMs to hPa)
        while (baro.isNotEmpty() && nowMs - baro.first().first > 2 * config.baroWindowMs) {
            baro.removeFirst()
        }
        // The reading from about one window ago, if any: a rise of the piston size since then.
        val reference = baro.firstOrNull { nowMs - it.first <= config.baroWindowMs }
        if (reference != null && reference.first != nowMs && hPa - reference.second >= config.baroPistonHpa) {
            baroPistonAtMs = nowMs
        }
        evaluate(nowMs)
    }

    /**
     * Along-track distance to the next mapped tunnel portal, metres; negative once inside, null
     * when there is no route or no coverage. Section 7.5: `UpcomingRoadObject.distanceToStart`,
     * or our own portal list as the fallback source -- the caller logs which.
     */
    fun onPortalDistance(nowMs: Long, metres: Float?) {
        val wasInside = portalDistanceM?.let { it <= 0f } == true
        portalDistanceM = metres
        if (metres != null && metres <= 0f && !wasInside) portalPassedAtMs = nowMs
        evaluate(nowMs)
    }

    /** The map's own opinion (`RouteProgress.inTunnel`); null when unknown. Entry only (section 7.5). */
    fun onMapInTunnel(nowMs: Long, inTunnel: Boolean?) {
        if (inTunnel == true && mapInTunnel != true) mapInTunnelAtMs = nowMs
        mapInTunnel = inTunnel
        evaluate(nowMs)
    }

    /**
     * The demo's manual override. On: tunnel mode now, whatever the signals say. Off: the exit
     * path runs -- through `EXIT_VERIFICATION` if fixes are arriving, otherwise the signals decide.
     */
    fun setForced(nowMs: Long, forced: Boolean) {
        if (this.forced == forced) return
        this.forced = forced
        if (forced) {
            if (state != TunnelState.TUNNEL_ACTIVE_IDR) {
                transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.MANUAL_ON, nowMs)
            }
        } else if (state == TunnelState.TUNNEL_ACTIVE_IDR && !fixSilent(nowMs)) {
            transition(TunnelState.EXIT_VERIFICATION, TunnelTrigger.MANUAL_OFF, nowMs)
        }
        evaluate(nowMs)
    }

    /** Call periodically (the estimator's publish tick is enough) so timeouts fire without a signal. */
    fun tick(nowMs: Long) = evaluate(nowMs)

    // ── The machine ──────────────────────────────────────────────────────────────────────

    private fun evaluate(nowMs: Long) {
        // At most one signal-driven transition per evaluation, then re-evaluate once, so that a
        // pre-arm and an entry arriving in the same event resolve in one call without looping.
        repeat(2) {
            val before = state
            step(nowMs)
            if (state == before) return
        }
    }

    private fun step(nowMs: Long) {
        if (forced) {
            if (state != TunnelState.TUNNEL_ACTIVE_IDR) {
                transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.MANUAL_ON, nowMs)
            }
            return
        }
        when (state) {
            TunnelState.GNSS_HEALTHY -> {
                when {
                    fixSilent(nowMs) && !cn0Healthy(nowMs) ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.GNSS_TIMEOUT, nowMs)
                    mapSaysEntered() ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.MAP_IN_TUNNEL, nowMs)
                    portalPassed() ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.PORTAL_PASSED, nowMs)
                    cn0Suspect() ->
                        transition(TunnelState.PRE_ARMED_ENTRY, TunnelTrigger.CN0_COLLAPSE, nowMs)
                    portalNear() ->
                        transition(TunnelState.PRE_ARMED_ENTRY, TunnelTrigger.PORTAL_NEAR, nowMs)
                    recent(luxDropAtMs, nowMs, config.transientWindowMs) ->
                        transition(TunnelState.PRE_ARMED_ENTRY, TunnelTrigger.LUX_DROP, nowMs)
                    recent(baroPistonAtMs, nowMs, config.transientWindowMs) ->
                        transition(TunnelState.PRE_ARMED_ENTRY, TunnelTrigger.BARO_PISTON, nowMs)
                }
            }

            TunnelState.PRE_ARMED_ENTRY -> {
                val luxConfirmed = recent(luxDropAtMs, nowMs, config.transientWindowMs) &&
                    recent(cn0DroppedAtMs, nowMs, config.transientWindowMs)
                when {
                    fixSilent(nowMs) ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.GNSS_TIMEOUT, nowMs)
                    mapSaysEntered() ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.MAP_IN_TUNNEL, nowMs)
                    portalPassed() ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.PORTAL_PASSED, nowMs)
                    luxConfirmed ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.LUX_DROP, nowMs)
                    cn0Lost() ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.CN0_LOST, nowMs)
                    preArmCleared(nowMs) ->
                        transition(TunnelState.GNSS_HEALTHY, TunnelTrigger.PRE_ARM_CLEARED, nowMs)
                }
            }

            TunnelState.TUNNEL_ACTIVE_IDR -> {
                // A fix arriving is handled in onGnssFix; here only the receiver's own report,
                // and only one made after entry (deviation 5).
                if (statusAtMs > stateEnteredMs && cn0Recovered()) {
                    transition(TunnelState.EXIT_VERIFICATION, TunnelTrigger.CN0_RECOVERED, nowMs)
                }
            }

            TunnelState.EXIT_VERIFICATION -> {
                // Entered on C/N0 recovery, the receiver gets the timeout to produce a fix.
                if (fixSilentSinceEntry(nowMs)) {
                    transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.GNSS_TIMEOUT, nowMs)
                }
            }

            TunnelState.SEAMLESS_RECONVERGENCE -> {
                when {
                    fixSilentSinceEntry(nowMs) ->
                        transition(TunnelState.TUNNEL_ACTIVE_IDR, TunnelTrigger.GNSS_TIMEOUT, nowMs)
                    nowMs - stateEnteredMs >= config.reconvergeSettleMs && !cn0Lost() ->
                        transition(TunnelState.GNSS_HEALTHY, TunnelTrigger.RECONVERGED, nowMs)
                }
            }
        }
    }

    private fun transition(to: TunnelState, trigger: TunnelTrigger, nowMs: Long) {
        val from = state
        state = to
        stateEnteredMs = nowMs
        if (from.suppressesGnss && !to.suppressesGnss) lastExitMs = nowMs
        when (to) {
            TunnelState.PRE_ARMED_ENTRY -> preArmHealthySinceMs = Long.MIN_VALUE
            TunnelState.EXIT_VERIFICATION -> consecutivePasses = 0
            else -> Unit
        }
        history.addLast(TunnelTransition(from, to, trigger, nowMs))
        while (history.size > config.historySize) history.removeFirst()
    }

    // ── Predicates ───────────────────────────────────────────────────────────────────────

    private fun fixSilent(nowMs: Long): Boolean = nowMs - lastFixMs > config.gnssTimeoutMs

    private fun fixSilentSinceEntry(nowMs: Long): Boolean =
        nowMs - maxOf(lastFixMs, stateEnteredMs) > config.gnssTimeoutMs

    private fun statusFresh(nowMs: Long): Boolean =
        statusAtMs != Long.MIN_VALUE && nowMs - statusAtMs <= config.statusFreshMs

    private fun cn0Healthy(nowMs: Long): Boolean {
        val cn0 = cn0Top4DbHz ?: return false
        return statusFresh(nowMs) && cn0 > config.cn0HealthyDbHz && satellitesUsed >= config.minSatsHealthy
    }

    /** A report has arrived and it is weak -- or it tracks nothing at all. */
    private fun cn0Suspect(): Boolean {
        if (statusAtMs == Long.MIN_VALUE) return false
        val cn0 = cn0Top4DbHz ?: return true
        return cn0 < config.cn0SuspectDbHz
    }

    private fun cn0Lost(): Boolean {
        if (statusAtMs == Long.MIN_VALUE) return false
        val cn0 = cn0Top4DbHz ?: return true
        return cn0 < config.cn0LostDbHz
    }

    private fun mapSaysEntered(): Boolean = mapInTunnel == true && mapInTunnelAtMs > lastExitMs

    private fun cn0Recovered(): Boolean {
        val cn0 = cn0Top4DbHz ?: return false
        return cn0 > config.cn0SuspectDbHz && satellitesUsed >= config.minSatsHealthy
    }

    private fun portalNear(): Boolean {
        val d = portalDistanceM ?: return false
        return d >= 0f && d < config.portalPreArmM
    }

    private fun portalPassed(): Boolean {
        val d = portalDistanceM ?: return false
        return d <= 0f && portalPassedAtMs > lastExitMs
    }

    private fun recent(atMs: Long, nowMs: Long, withinMs: Long): Boolean =
        atMs != Long.MIN_VALUE && nowMs - atMs <= withinMs

    /** Deviation 1: every signal healthy, continuously, for the clear window. */
    private fun preArmCleared(nowMs: Long): Boolean {
        val healthyNow = cn0Healthy(nowMs) && !fixSilent(nowMs) && !portalNear() && !mapSaysEntered() &&
            !recent(luxDropAtMs, nowMs, config.transientWindowMs) &&
            !recent(baroPistonAtMs, nowMs, config.transientWindowMs)
        if (!healthyNow) {
            preArmHealthySinceMs = Long.MIN_VALUE
            return false
        }
        if (preArmHealthySinceMs == Long.MIN_VALUE) preArmHealthySinceMs = nowMs
        return nowMs - preArmHealthySinceMs >= config.preArmClearMs
    }
}

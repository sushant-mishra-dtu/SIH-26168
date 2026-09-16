package com.sih.idr.demo.backend.routing

import kotlin.math.exp
import kotlin.math.max

/**
 * The speed the ETA is divided by.
 *
 * The filter's instantaneous speed is the wrong thing to put under `remaining / speed`: it is
 * published at 30 Hz, it wobbles by a metre per second between ticks, and it is zero at every
 * red light. Dividing 7 km by it makes the headline ETA flip between "13 min" and "52 min" from
 * one frame to the next (the flicker in the 14 Sep demo clip).
 *
 * This keeps a slow exponential average of the speed *while moving*, seeded from the route's
 * own planned average, so:
 *  - noise at 30 Hz is averaged out over [TAU_SEC];
 *  - standing still holds the last pace instead of blowing the ETA up;
 *  - a walked route honestly settles to a walking ETA rather than snapping to a 30 km/h guess.
 */
class EtaPaceModel {

    /** The pace the ETA should currently be computed from, m/s. Never below [MIN_PACE_MPS]. */
    var paceMps: Float = DEFAULT_PACE_MPS
        private set

    private var lastSampleMs: Long = Long.MIN_VALUE

    /** Seed from [route]'s planned average; called whenever the active route changes. */
    fun reset(route: NavigationRoute?) {
        val planned = if (route != null && route.durationSeconds > 0L && route.distanceMeters > 0f) {
            route.distanceMeters / route.durationSeconds
        } else {
            DEFAULT_PACE_MPS
        }
        paceMps = max(planned, MIN_PACE_MPS)
        lastSampleMs = Long.MIN_VALUE
    }

    /**
     * Feed one speed sample at [nowMs] (a monotonic clock). Samples below [MOVING_MIN_MPS] are
     * treated as "stopped" and do not move the average; the clock still advances so a long stop
     * is not replayed as one huge step when motion resumes.
     */
    fun update(speedMps: Float, nowMs: Long) {
        val dtSec = if (lastSampleMs == Long.MIN_VALUE) 0f else (nowMs - lastSampleMs) / 1000f
        lastSampleMs = nowMs
        if (speedMps < MOVING_MIN_MPS || dtSec <= 0f) return
        val alpha = 1f - exp(-dtSec / TAU_SEC)
        paceMps = max(paceMps + alpha * (speedMps - paceMps), MIN_PACE_MPS)
    }

    companion object {
        /** Time constant of the moving-speed average. Long enough that 30 Hz jitter vanishes. */
        const val TAU_SEC = 45f
        /** Below this the vehicle is "stopped" and the sample is ignored. */
        const val MOVING_MIN_MPS = 1.0f
        /** Floor on the pace so a bad seed can never yield a multi-hour ETA for a short hop. */
        const val MIN_PACE_MPS = 1.0f
        /** ~30 km/h; used only when the route carries no planned duration. */
        const val DEFAULT_PACE_MPS = 8.33f
    }
}

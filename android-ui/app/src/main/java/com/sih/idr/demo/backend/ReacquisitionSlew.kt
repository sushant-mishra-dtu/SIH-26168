package com.sih.idr.demo.backend

import kotlin.math.abs
import kotlin.math.hypot

/**
 * The offset that hides a re-acquisition step from the drawn track (D-128).
 *
 * A pose dead-reckoned through a tunnel is wrong by whatever it accumulated inside, so the first
 * GNSS fix that applies at the exit is a step, not a nudge. Applying it to the state is right --
 * it is the better answer, and half-applying it leaves the next fix outside the chi-square gate
 * again -- but *drawing* it puts a straight segment across the map and a vertex out in a field,
 * which is what a 14 Sep field run showed on the Wazirabad approach. AGENTS.md's thesis is that
 * one filter means no position jump at a tunnel mouth; this is that promise kept on the display
 * side, for the demo estimator that does have one.
 *
 * So the correction goes into the state whole and into this offset with the opposite sign: the
 * reported pose is `state + offset`, which at the instant of the step is exactly where the pose
 * was before it, and the offset then decays to nothing over [TAU_SEC]. The track bends onto the
 * road over a couple of seconds instead of jumping to it, and nothing that is drawn ever moves
 * discontinuously.
 *
 * Three things this deliberately is not:
 *
 *  - **Not feedback.** Nothing here is read back into the estimate. The filter's pose is the fix's
 *    pose from the moment it is applied; only the rendering lags.
 *  - **Not unbounded.** Past [MAX_M] the remainder is drawn as the step it is. A track that slid
 *    200 m sideways without a break would be claiming a continuity the estimate does not have.
 *  - **Not free.** While an offset is running the drawn point is knowingly off the best estimate,
 *    so its magnitude is added to the reported sigma and the ellipse still covers the estimate.
 *
 * Pure Kotlin, time passed in as `dtSec`, for the reason `TunnelFsm` and `CourseTracker` are
 * (D-126, D-127): a rule a laptop cannot drive is a rule nobody can argue about.
 */
class ReacquisitionSlew {

    /** North component of the offset added to the state to get the reported pose, metres. */
    var northM: Float = 0f
        private set

    /** East component of the offset added to the state to get the reported pose, metres. */
    var eastM: Float = 0f
        private set

    /** How far the drawn point currently sits from the estimate, metres. */
    val magnitudeM: Float get() = hypot(northM, eastM)

    val active: Boolean get() = northM != 0f || eastM != 0f

    /**
     * A correction of [dNorthM], [dEastM] has just been applied to the state. Take the same step
     * backwards, so that the reported pose does not move at this instant.
     *
     * Clamped to [MAX_M] *after* accumulation, so a second correction arriving while the first is
     * still running adds to it rather than replacing it, and neither can push the drawn point
     * further than the cap from the estimate.
     */
    fun absorb(dNorthM: Float, dEastM: Float) {
        northM = (northM - dNorthM).coerceIn(-MAX_M, MAX_M)
        eastM = (eastM - dEastM).coerceIn(-MAX_M, MAX_M)
    }

    /** Run the offset off over [dtSec] seconds of sensor time. */
    fun decay(dtSec: Float) {
        if (!active) return
        val k = (dtSec / TAU_SEC).coerceIn(0f, 1f)
        northM -= northM * k
        eastM -= eastM * k
        if (abs(northM) < EPSILON_M && abs(eastM) < EPSILON_M) {
            northM = 0f
            eastM = 0f
        }
    }

    fun reset() {
        northM = 0f
        eastM = 0f
    }

    companion object {
        /**
         * Time constant of the decay. 0.7 s puts ~94% of a correction behind the track inside the
         * machine's 2 s `TunnelFsmConfig.reconvergeSettleMs`, so `SEAMLESS_RECONVERGENCE` is a
         * state in which something actually reconverges rather than a label on a jump that has
         * already happened. Slow enough that a 40 m correction reads as a bend, not a corner.
         */
        const val TAU_SEC = 0.7f

        /** Under the width of the puck: zeroed rather than left tailing off forever. */
        const val EPSILON_M = 0.05f

        /** The largest correction the display will hide; see the class note. */
        const val MAX_M = 75f
    }
}

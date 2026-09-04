package org.idr26168.logger

import kotlin.math.sqrt

/**
 * Achieved rate and timestamp jitter for one sensor stream. This is the deliverable.
 *
 * `docs/IMPLEMENTATION_PLAN.md` section 4, seat A: "measure the actual achieved sample rate and
 * timestamp jitter on each team device. The nominal rate is not the real rate." Everything else in
 * this app exists so that these numbers can be produced honestly.
 *
 * Design constraints:
 *  - `add` runs on the sensor callback thread at up to 400 Hz. It must be O(1) and allocation-free.
 *  - Memory must not grow with drive length. A 40-minute drive at 200 Hz is 480,000 intervals; we
 *    keep a fixed histogram instead of the samples.
 *  - Percentiles come out of the histogram, so they carry its bin width (100 us) as resolution.
 *    p95 of 9.9 ms is reported as such and not as 9.9137 ms, because we do not have that.
 *
 * Two things are counted rather than smoothed away, because both are real and both are invisible
 * in a mean:
 *  - **Non-monotonic stamps.** A batched FIFO can deliver events out of order. A negative dt is
 *    not noise, it is a stream we cannot integrate; it gets its own counter.
 *  - **Batch arrivals.** Events whose *timestamps* are a clean 5 ms apart but which all arrive in
 *    one callback burst. The stream is fine for post-processing and useless for a real-time
 *    filter, and only the arrival clock can tell the two apart.
 */
class RateStats(private val label: String, private val requestedHz: Double) {

    private val bins = IntArray(BIN_COUNT)
    private var overflow: Long = 0
    private var intervals: Long = 0
    private var events: Long = 0
    private var firstNs: Long = 0
    private var lastNs: Long = 0
    private var lastArrivalNs: Long = 0
    private var minNs: Long = Long.MAX_VALUE
    private var maxNs: Long = 0
    private var mean: Double = 0.0
    private var m2: Double = 0.0
    private var nonMonotonic: Long = 0
    private var gapsOver3x: Long = 0
    private var batchArrivals: Long = 0

    @Synchronized
    fun add(eventNs: Long, arrivalNs: Long) {
        if (events == 0L) {
            firstNs = eventNs
            lastNs = eventNs
            lastArrivalNs = arrivalNs
            events = 1
            return
        }

        val dt = eventNs - lastNs
        if (dt <= 0) {
            nonMonotonic++
        } else {
            intervals++
            if (dt < minNs) minNs = dt
            if (dt > maxNs) maxNs = dt

            // Welford, in doubles of nanoseconds. At 1e9 ns the precision is ~1e-7 ns; fine.
            val d = dt.toDouble()
            val delta = d - mean
            mean += delta / intervals
            m2 += delta * (d - mean)

            val bin = (dt / BIN_WIDTH_NS).toInt()
            if (bin in bins.indices) bins[bin]++ else overflow++

            if (requestedHz > 0 && dt > 3.0 * 1e9 / requestedHz) gapsOver3x++

            // Arrival much tighter than the event spacing => the FIFO flushed a batch.
            val arrivalGap = arrivalNs - lastArrivalNs
            if (arrivalGap >= 0 && arrivalGap * 4 < dt) batchArrivals++
            lastNs = eventNs
        }
        lastArrivalNs = arrivalNs
        events++
    }

    @Synchronized
    fun snapshot(): Snapshot {
        val spanNs = if (events > 1) lastNs - firstNs else 0L
        val spanS = spanNs / 1e9
        return Snapshot(
            label = label,
            requestedHz = requestedHz,
            events = events,
            spanS = spanS,
            achievedHz = if (spanS > 0) (events - 1) / spanS else 0.0,
            dtMinMs = if (minNs == Long.MAX_VALUE) 0.0 else minNs / 1e6,
            dtMeanMs = mean / 1e6,
            dtMedianMs = percentileMs(0.50),
            dtP95Ms = percentileMs(0.95),
            dtP99Ms = percentileMs(0.99),
            dtMaxMs = maxNs / 1e6,
            dtStdevMs = if (intervals > 1) sqrt(m2 / (intervals - 1)) / 1e6 else 0.0,
            nonMonotonic = nonMonotonic,
            gapsOver3x = gapsOver3x,
            batchArrivals = batchArrivals,
            binWidthMs = BIN_WIDTH_NS / 1e6,
        )
    }

    /** Histogram percentile. Returns the *upper edge* of the containing bin, in ms. */
    private fun percentileMs(q: Double): Double {
        if (intervals == 0L) return 0.0
        val target = (q * intervals).toLong().coerceAtLeast(1L)
        var cum = 0L
        for (i in bins.indices) {
            cum += bins[i]
            if (cum >= target) return ((i + 1) * BIN_WIDTH_NS) / 1e6
        }
        // Everything past the last bin: report the observed max rather than the bin edge, which
        // would be a lie in the safe-looking direction.
        return maxNs / 1e6
    }

    data class Snapshot(
        val label: String,
        val requestedHz: Double,
        val events: Long,
        val spanS: Double,
        val achievedHz: Double,
        val dtMinMs: Double,
        val dtMeanMs: Double,
        val dtMedianMs: Double,
        val dtP95Ms: Double,
        val dtP99Ms: Double,
        val dtMaxMs: Double,
        val dtStdevMs: Double,
        val nonMonotonic: Long,
        val gapsOver3x: Long,
        val batchArrivals: Long,
        val binWidthMs: Double,
    )

    companion object {
        /** 100 us bins out to 2 s: 20,000 ints = 80 KB per stream. */
        private const val BIN_WIDTH_NS = 100_000L
        private const val BIN_COUNT = 20_000
    }
}

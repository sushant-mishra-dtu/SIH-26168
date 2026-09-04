package org.idr26168.logger

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * [RateStats] is the class that produces the deliverable, so it is the class that has to be right.
 *
 * `docs/IMPLEMENTATION_PLAN.md` section 4 asks seat A for the achieved sample rate and the
 * timestamp jitter per device. Every one of those numbers comes out of `snapshot()`. Until a real
 * drive exists there is nothing to check them against, so what can be checked is the arithmetic:
 * feed a delta-t sequence whose median, p95 and standard deviation are known on paper, and assert
 * the class reproduces them.
 *
 * Two of these tests pin behaviour that looks like a bug and is not. Both are documented in the
 * class and in `android/HANDOVER.md` section 5, and both would otherwise be "fixed" by the next
 * person to read the output: the histogram reports a bin's upper edge, and an interval past the
 * last bin reports the observed maximum instead. A test is the only place that distinction
 * survives a well-meant tidy-up.
 */
class RateStatsTest {

    private val ms = 1_000_000L

    /** `count` events spaced `dtNs` apart in event time, `arrivalDtNs` apart on arrival. */
    private fun stream(
        count: Int,
        dtNs: Long,
        requestedHz: Double = 100.0,
        arrivalDtNs: Long = dtNs,
        startNs: Long = 1_000_000_000L,
    ): RateStats.Snapshot {
        val stats = RateStats("accelerometer", requestedHz)
        var event = startNs
        var arrival = startNs
        repeat(count) {
            stats.add(event, arrival)
            event += dtNs
            arrival += arrivalDtNs
        }
        return stats.snapshot()
    }

    // -- the headline numbers -------------------------------------------------------------------

    @Test
    fun `a perfectly regular 100 Hz stream reports 100 Hz`() {
        // 101 events at 10 ms is 100 intervals spanning exactly one second.
        val s = stream(count = 101, dtNs = 10 * ms)

        assertEquals(101L, s.events)
        assertEquals(1.0, s.spanS, 1e-12)
        assertEquals(100.0, s.achievedHz, 1e-9)
    }

    @Test
    fun `achieved rate counts intervals and not events, so one event is not an infinite rate`() {
        val none = stream(count = 0, dtNs = 10 * ms)
        assertEquals(0L, none.events)
        assertEquals(0.0, none.achievedHz, 0.0)

        val one = stream(count = 1, dtNs = 10 * ms)
        assertEquals(1L, one.events)
        assertEquals(0.0, one.achievedHz, 0.0)
        assertEquals(0.0, one.spanS, 0.0)
    }

    @Test
    fun `an empty stream produces finite zeros rather than NaN`() {
        val s = stream(count = 0, dtNs = 10 * ms)
        // Every one of these is written straight into the sidecar JSON, and a NaN is not a value
        // JSONObject can write. The sidecar is how the measurement gets reported at all.
        for (v in listOf(
            s.spanS, s.achievedHz, s.dtMinMs, s.dtMeanMs, s.dtMedianMs,
            s.dtP95Ms, s.dtP99Ms, s.dtMaxMs, s.dtStdevMs,
        )) {
            assertTrue("expected a finite zero, got $v", v.isFinite())
            assertEquals(0.0, v, 0.0)
        }
    }

    @Test
    fun `min mean and max come straight from the timestamps`() {
        val s = stream(count = 101, dtNs = 10 * ms)
        assertEquals(10.0, s.dtMinMs, 1e-9)
        assertEquals(10.0, s.dtMeanMs, 1e-9)
        assertEquals(10.0, s.dtMaxMs, 1e-9)
    }

    // -- Welford ----------------------------------------------------------------------------------

    @Test
    fun `a constant interval has zero jitter`() {
        assertEquals(0.0, stream(count = 101, dtNs = 10 * ms).dtStdevMs, 1e-9)
    }

    @Test
    fun `standard deviation matches the sample stdev computed by hand`() {
        // Intervals 8, 12, 8, 12 ms: mean 10, deviations +-2, sum of squares 16, n-1 = 3.
        // Sample stdev = sqrt(16 / 3) = 2.309401... ms.
        val stats = RateStats("accelerometer", 100.0)
        var t = 0L
        for (dt in listOf(8L, 12L, 8L, 12L)) {
            stats.add(t, t)
            t += dt * ms
        }
        stats.add(t, t)

        val s = stats.snapshot()
        assertEquals(10.0, s.dtMeanMs, 1e-9)
        assertEquals(Math.sqrt(16.0 / 3.0), s.dtStdevMs, 1e-9)
    }

    @Test
    fun `stdev needs two intervals before it means anything`() {
        val stats = RateStats("accelerometer", 100.0)
        stats.add(0, 0)
        stats.add(10 * ms, 10 * ms)
        assertEquals(0.0, stats.snapshot().dtStdevMs, 0.0)
    }

    // -- the histogram, and what it can and cannot say ---------------------------------------------

    @Test
    fun `percentiles are the upper edge of a 100 microsecond bin, not an exact quantile`() {
        // HANDOVER.md section 5, first bullet. A dead-regular 10.0 ms stream falls in the bin
        // [10.0, 10.1) ms and is reported as 10.1 -- deliberately, because bounded memory over a
        // 40-minute drive is worth more than the last decimal, and reporting 10.0 would claim a
        // resolution the histogram does not have.
        val s = stream(count = 101, dtNs = 10 * ms)

        assertEquals(0.1, s.binWidthMs, 1e-12)
        assertEquals(10.1, s.dtMedianMs, 1e-9)
        assertEquals(10.1, s.dtP95Ms, 1e-9)
        assertEquals(10.1, s.dtP99Ms, 1e-9)
        // The exact figures stay exact; only the percentiles carry the bin width.
        assertEquals(10.0, s.dtMinMs, 1e-9)
        assertEquals(10.0, s.dtMaxMs, 1e-9)
    }

    @Test
    fun `the reported percentile never understates the interval it describes`() {
        // The direction of the rounding is the part that matters. p95 is the number used to argue
        // a stream is good enough; one that rounded down would make a marginal device look passable.
        for (dtMs in listOf(2L, 5L, 10L, 20L)) {
            val s = stream(count = 51, dtNs = dtMs * ms)
            assertTrue(
                "p95 ${s.dtP95Ms} ms understates the true interval $dtMs ms",
                s.dtP95Ms >= dtMs.toDouble(),
            )
            assertTrue(
                "p95 ${s.dtP95Ms} ms is more than one bin above $dtMs ms",
                s.dtP95Ms <= dtMs + s.binWidthMs + 1e-9,
            )
        }
    }

    @Test
    fun `a percentile separates a slow tail from the median`() {
        // 90 intervals at 10 ms and 10 at 50 ms. The median sits in the fast group and p95 in the
        // slow one, which is the whole reason a percentile is reported instead of a mean.
        val stats = RateStats("accelerometer", 100.0)
        var t = 0L
        stats.add(t, t)
        repeat(90) { t += 10 * ms; stats.add(t, t) }
        repeat(10) { t += 50 * ms; stats.add(t, t) }

        val s = stats.snapshot()
        assertEquals(10.1, s.dtMedianMs, 1e-9)
        assertEquals(50.1, s.dtP95Ms, 1e-9)
        assertEquals(50.0, s.dtMaxMs, 1e-9)
        assertEquals(10.0, s.dtMinMs, 1e-9)
    }

    @Test
    fun `an interval past the last bin reports the observed maximum, not the bin edge`() {
        // 20,000 bins of 100 us is a 2 s ceiling. A longer gap overflows, and the class reports the
        // real maximum rather than "2 s", which would be a lie in the reassuring direction.
        val stats = RateStats("accelerometer", 100.0)
        stats.add(0, 0)
        stats.add(3_000L * ms, 3_000L * ms)

        val s = stats.snapshot()
        assertEquals(3000.0, s.dtMaxMs, 1e-9)
        assertEquals(3000.0, s.dtMedianMs, 1e-9)
    }

    // -- the counters a mean would hide -------------------------------------------------------------

    @Test
    fun `a backwards timestamp is counted and never integrated`() {
        // A batched FIFO can deliver out of order. A negative dt is not noise, it is a stream that
        // cannot be integrated, so it gets a counter of its own and stays out of the statistics.
        val stats = RateStats("accelerometer", 100.0)
        stats.add(0, 0)
        stats.add(10 * ms, 10 * ms)
        stats.add(5 * ms, 11 * ms)   // backwards
        stats.add(20 * ms, 20 * ms)

        val s = stats.snapshot()
        assertEquals(1L, s.nonMonotonic)
        assertEquals(4L, s.events)
        // Both surviving intervals are 10 ms; the -5 ms never reached the mean or the minimum.
        assertEquals(10.0, s.dtMeanMs, 1e-9)
        assertEquals(10.0, s.dtMinMs, 1e-9)
        assertEquals(10.0, s.dtMaxMs, 1e-9)
        assertEquals(0.0, s.dtStdevMs, 1e-9)
    }

    @Test
    fun `a repeated timestamp counts as non-monotonic rather than as a zero interval`() {
        val stats = RateStats("accelerometer", 100.0)
        stats.add(10 * ms, 10 * ms)
        stats.add(10 * ms, 11 * ms)
        val s = stats.snapshot()
        assertEquals(1L, s.nonMonotonic)
        // A zero interval admitted to the histogram would drag the median toward zero and make a
        // stalled stream look fast.
        assertEquals(0.0, s.dtMeanMs, 0.0)
    }

    @Test
    fun `gaps beyond three times the requested period are counted`() {
        // 100 Hz requested means a 10 ms period and so a 30 ms threshold.
        val stats = RateStats("accelerometer", 100.0)
        var t = 0L
        stats.add(t, t)
        t += 10 * ms; stats.add(t, t)   // nominal
        t += 29 * ms; stats.add(t, t)   // slow, but under 3x
        t += 40 * ms; stats.add(t, t)   // over 3x
        t += 31 * ms; stats.add(t, t)   // over 3x

        assertEquals(2L, stats.snapshot().gapsOver3x)
    }

    @Test
    fun `a stream with no requested rate reports no gaps rather than dividing by zero`() {
        val stats = RateStats("gnss_fix", 0.0)
        stats.add(0, 0)
        stats.add(60_000L * ms, 60_000L * ms)
        assertEquals(0L, stats.snapshot().gapsOver3x)
    }

    @Test
    fun `events that arrive in a burst are counted as batched`() {
        // Timestamps a clean 10 ms apart, all delivered 1 ms apart in one FIFO flush. Post
        // processing cannot tell the difference; a real-time filter can, and only the arrival
        // clock records it.
        val batched = stream(count = 4, dtNs = 10 * ms, arrivalDtNs = 1 * ms)
        assertEquals(3L, batched.batchArrivals)

        // The control: arrival tracks the event clock, so nothing is batched.
        val live = stream(count = 4, dtNs = 10 * ms)
        assertEquals(0L, live.batchArrivals)
    }

    @Test
    fun `the requested rate is reported back unchanged so the sidecar records what was asked`() {
        // "We asked for 200 Hz and got 100" is the sentence the sidecar has to be able to make.
        val s = stream(count = 51, dtNs = 10 * ms, requestedHz = 200.0)
        assertEquals(200.0, s.requestedHz, 0.0)
        assertEquals(100.0, s.achievedHz, 1e-9)
        assertEquals("accelerometer", s.label)
    }
}

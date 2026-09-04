package org.idr26168.logger

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Date
import java.util.TimeZone

/**
 * Timebase classification, and the date column.
 *
 * [SessionClock] exists because `SensorEvent.timestamp` has an unspecified base. On almost every
 * device it is `elapsedRealtimeNanos`, on some it is `uptimeNanos` -- which stops during deep
 * sleep -- and the difference is invisible on a bench and worth minutes after a drive with the
 * screen off. The class refuses to assume, measures instead, and writes what it concluded into
 * the sidecar so that a suspect device is identifiable from the file rather than from memory.
 *
 * Which makes the classifier itself the thing to test: it is the only part of the app whose
 * failure mode is a recording that looks completely normal and is dated wrong.
 *
 * These tests run against the stubbed android.jar, so `SystemClock.elapsedRealtimeNanos()` returns
 * 0 and the boot anchor equals `System.currentTimeMillis()`. That is a device that has just
 * booted -- a real state, not an impossible one -- so the mapping under test is the real mapping.
 */
class SessionClockTest {

    private val second = 1_000_000_000L

    // -- classification -----------------------------------------------------------------------------

    @Test
    fun `a clock with no probes reports UNKNOWN rather than guessing`() {
        assertEquals(SessionClock.Timebase.UNKNOWN, SessionClock().timebase())
    }

    @Test
    fun `stamps that track elapsed realtime classify as ELAPSED_REALTIME`() {
        val clock = SessionClock()
        // The device has been asleep for 3 s, so the two bases have diverged and the event stamp
        // follows elapsed realtime.
        repeat(100) { i ->
            val event = 5 * second + i * 10_000_000L
            clock.probe(
                eventNs = event,
                arrivalElapsedNs = event + 100_000L,   // 100 us of delivery latency
                arrivalUptimeNs = event - 3 * second,
            )
        }
        assertEquals(SessionClock.Timebase.ELAPSED_REALTIME, clock.timebase())
    }

    @Test
    fun `stamps that track uptime classify as UPTIME`() {
        val clock = SessionClock()
        repeat(100) { i ->
            val event = 2 * second + i * 10_000_000L
            clock.probe(
                eventNs = event,
                arrivalElapsedNs = event + 3 * second,
                arrivalUptimeNs = event + 100_000L,
            )
        }
        assertEquals(SessionClock.Timebase.UPTIME, clock.timebase())
    }

    @Test
    fun `stamps on a base that matches neither classify as UNKNOWN`() {
        // The case the sidecar has to be able to report: this device's recordings are suspect, and
        // the number to argue about is in the file.
        val clock = SessionClock()
        repeat(100) {
            clock.probe(eventNs = 1000L, arrivalElapsedNs = 5 * second, arrivalUptimeNs = 2 * second)
        }
        assertEquals(SessionClock.Timebase.UNKNOWN, clock.timebase())
    }

    @Test
    fun `when both bases agree the documented intent wins`() {
        // A phone that has not slept since boot reports the two identically, which is the common
        // case in a cradle. ELAPSED_REALTIME is chosen there because it is the documented intent
        // and the two are numerically the same until the first deep sleep, so it costs nothing.
        val clock = SessionClock()
        repeat(100) { i ->
            val event = 5 * second + i * 10_000_000L
            clock.probe(event, event + 100_000L, event + 100_000L)
        }
        assertEquals(SessionClock.Timebase.ELAPSED_REALTIME, clock.timebase())
    }

    @Test
    fun `classification needs more than ninety percent agreement`() {
        // The threshold is a strict "greater than 0.9", so exactly nine in ten is not enough. A
        // device that agrees only nine times in ten is a device whose stamps drift against both
        // bases, and calling that ELAPSED_REALTIME would date the drive confidently and wrongly.
        val onTheLine = SessionClock()
        repeat(90) { i ->
            val event = 5 * second + i * 10_000_000L
            onTheLine.probe(event, event + 100_000L, event - 3 * second)
        }
        repeat(10) {
            onTheLine.probe(eventNs = 1000L, arrivalElapsedNs = 5 * second, arrivalUptimeNs = 9 * second)
        }
        assertEquals(SessionClock.Timebase.UNKNOWN, onTheLine.timebase())

        val overTheLine = SessionClock()
        repeat(91) { i ->
            val event = 5 * second + i * 10_000_000L
            overTheLine.probe(event, event + 100_000L, event - 3 * second)
        }
        repeat(9) {
            overTheLine.probe(eventNs = 1000L, arrivalElapsedNs = 5 * second, arrivalUptimeNs = 9 * second)
        }
        assertEquals(SessionClock.Timebase.ELAPSED_REALTIME, overTheLine.timebase())
    }

    @Test
    fun `agreement is judged within one second, so ordinary latency does not disqualify a device`() {
        val clock = SessionClock()
        repeat(100) { i ->
            val event = 5 * second + i * 10_000_000L
            // 999 ms of delivery latency: ugly, still the same base.
            clock.probe(event, event + 999_000_000L, event - 30 * second)
        }
        assertEquals(SessionClock.Timebase.ELAPSED_REALTIME, clock.timebase())
    }

    // -- the offset ----------------------------------------------------------------------------------

    @Test
    fun `the reported offset is the median of arrival minus event`() {
        val clock = SessionClock()
        // Offsets 1, 2, 3, 4, 5 ms. The median of five is the third.
        for (offsetMs in listOf(3L, 1L, 5L, 2L, 4L)) {
            clock.probe(eventNs = second, arrivalElapsedNs = second + offsetMs * 1_000_000L, arrivalUptimeNs = second)
        }
        assertEquals(3_000_000L, clock.medianOffsetNs())
    }

    @Test
    fun `a clock with no probes reports a zero offset rather than dividing by nothing`() {
        assertEquals(0L, SessionClock().medianOffsetNs())
    }

    @Test
    fun `the median is taken over a bounded reservoir so a long drive cannot grow it`() {
        // The reservoir holds the first 4096 samples and drops the rest. That is a real decision --
        // memory must not grow with drive length -- and it means the offset describes the start of
        // the recording, not all of it. Asserted so it is a property and not a surprise.
        val clock = SessionClock()
        repeat(4096) {
            clock.probe(eventNs = second, arrivalElapsedNs = second + 1_000_000L, arrivalUptimeNs = second)
        }
        repeat(2000) {
            clock.probe(eventNs = second, arrivalElapsedNs = second + 999_000_000L, arrivalUptimeNs = second)
        }
        assertEquals(1_000_000L, clock.medianOffsetNs())
    }

    // -- the wall clock mapping ------------------------------------------------------------------------

    @Test
    fun `two sensor stamps map to wall times the same distance apart`() {
        // The property that matters, and it holds whatever the boot anchor is: the date column and
        // the time_since_start_ms column are derived from the same instant, so two rows written in
        // one tick cannot disagree with each other.
        val clock = SessionClock()
        val a = 5 * second
        val b = a + 1_234_000_000L
        assertEquals(1234L, clock.wallMsForSensorNs(b) - clock.wallMsForSensorNs(a))
    }

    @Test
    fun `the mapping is anchored and does not move between calls`() {
        val clock = SessionClock()
        val first = clock.wallMsForSensorNs(5 * second)
        Thread.sleep(5)
        assertEquals(first, clock.wallMsForSensorNs(5 * second))
    }

    // -- the date column --------------------------------------------------------------------------------

    @Test
    fun `the date pattern uses a dot before the milliseconds`() {
        // D-107. Three spellings are in play and only the dot parses on both sides of D-086, which
        // has since landed on main. Choosing the colon to look like the dataset would buy
        // authenticity and cost compatibility.
        assertEquals("yyyy-MM-dd HH:mm:ss.SSS", SessionClock.DATE_PATTERN)
        assertTrue(SessionClock.DATE_PATTERN.endsWith("ss.SSS"))
    }

    @Test
    fun `a formatted date matches the shape the loader parses`() {
        // The JVM-side half of tests-test_android_logger_schema.py, which asserts the same shape
        // against eval-loaders-truth.py's live pattern. Both halves have to hold: that file checks
        // the loader accepts the pattern, this one checks the app emits it.
        val format = SessionClock.dateFormat()
        format.timeZone = TimeZone.getTimeZone("UTC")
        val text = format.format(Date(0L))

        assertEquals("1970-01-01 00:00:00.000", text)
        assertTrue(text, Regex("""^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$""").matches(text))
    }

    @Test
    fun `the date carries milliseconds and does not round them away`() {
        val format = SessionClock.dateFormat()
        format.timeZone = TimeZone.getTimeZone("UTC")
        assertEquals("1970-01-01 00:00:00.123", format.format(Date(123L)))
        assertEquals("1970-01-01 00:00:01.007", format.format(Date(1007L)))
    }

    @Test
    fun `the date carries no quotes, unlike the dataset it is compared against`() {
        // IO-VNBD wraps each value in literal single quotes. That is a defect in a file we are not
        // writing, and copying it forward to look authentic is how it becomes permanent.
        val format = SessionClock.dateFormat()
        format.timeZone = TimeZone.getTimeZone("UTC")
        val text = format.format(Date(0L))
        assertTrue(text, !text.contains("'"))
        assertTrue(text, !text.contains(","))
    }

    @Test
    fun `each formatter is a fresh instance because SimpleDateFormat is not thread safe`() {
        // dateFormat() is called from the service and could be called from a test or a future
        // exporter on another thread. Sharing one instance across threads corrupts the output
        // silently rather than throwing.
        assertTrue(SessionClock.dateFormat() !== SessionClock.dateFormat())
    }
}

package org.idr26168.logger

import android.os.SystemClock
import java.util.Locale
import java.util.TimeZone
import kotlin.math.abs

/**
 * The one place that converts a sensor timestamp into a wall clock, and the one place that admits
 * it might be wrong.
 *
 * `SensorEvent.timestamp` is documented as "the time in nanoseconds at which the event happened"
 * on an unspecified base. In practice it is [SystemClock.elapsedRealtimeNanos] on almost every
 * device -- but not all: some report [SystemClock.uptimeNanos], which stops during deep sleep, and
 * a few report a base that drifts against both. The difference does not show up on a bench and
 * does show up as a silently wrong `date` column after a drive with the screen off.
 *
 * So this class does not assume. It measures the offset on every event, keeps a running median,
 * and reports which base the numbers are consistent with. The classification goes in the session
 * sidecar; if it comes back `UNKNOWN` on a team device, that device's recordings are suspect and
 * the number to argue about is in the file rather than in someone's memory.
 *
 * D-013 applies here too: `dt` comes from real timestamps and is never nominal.
 */
class SessionClock {

    enum class Timebase { ELAPSED_REALTIME, UPTIME, UNKNOWN }

    /** Wall-clock ms at the instant of boot, i.e. the constant that maps elapsedRealtime -> UTC. */
    private val bootWallMs: Long
    private val startedWallMs: Long
    private val startedElapsedNs: Long

    /** Reservoir of (elapsedRealtimeNanos - event.timestamp) samples, for the median. */
    private val offsetSamples = LongArray(OFFSET_SAMPLE_CAP)
    private var offsetCount = 0
    private var uptimeAgreeing = 0
    private var elapsedAgreeing = 0
    private var probed = 0

    init {
        // Read the pair as close together as possible; the two calls are microseconds apart and
        // that is the whole accuracy of this mapping.
        val elapsed = SystemClock.elapsedRealtimeNanos()
        val wall = System.currentTimeMillis()
        startedElapsedNs = elapsed
        startedWallMs = wall
        bootWallMs = wall - elapsed / 1_000_000L
    }

    /**
     * Feed one raw sensor timestamp, with the arrival time captured in the same callback.
     * Cheap: a subtraction, two comparisons and a bounded array write.
     */
    @Synchronized
    fun probe(eventNs: Long, arrivalElapsedNs: Long, arrivalUptimeNs: Long) {
        probed++
        val dElapsed = abs(arrivalElapsedNs - eventNs)
        val dUptime = abs(arrivalUptimeNs - eventNs)
        // "Agreeing" means the event stamp is within a second of that base at arrival. A stamp on
        // the wrong base is out by however long the device has spent asleep, which is minutes.
        if (dElapsed < ONE_SECOND_NS) elapsedAgreeing++
        if (dUptime < ONE_SECOND_NS) uptimeAgreeing++
        if (offsetCount < OFFSET_SAMPLE_CAP) {
            offsetSamples[offsetCount++] = arrivalElapsedNs - eventNs
        }
    }

    @Synchronized
    fun timebase(): Timebase {
        if (probed == 0) return Timebase.UNKNOWN
        val elapsedFrac = elapsedAgreeing.toDouble() / probed
        val uptimeFrac = uptimeAgreeing.toDouble() / probed
        // Both agree on a device that has never slept since boot, which is the common case on a
        // phone in a cradle. Prefer ELAPSED_REALTIME there: it is the documented intent, and the
        // two are numerically identical until the first deep sleep, so the choice costs nothing.
        return when {
            elapsedFrac > AGREEMENT_THRESHOLD -> Timebase.ELAPSED_REALTIME
            uptimeFrac > AGREEMENT_THRESHOLD -> Timebase.UPTIME
            else -> Timebase.UNKNOWN
        }
    }

    /** Median of (arrival - event), in ns. Sensor latency plus any base offset, undifferentiated. */
    @Synchronized
    fun medianOffsetNs(): Long {
        if (offsetCount == 0) return 0L
        val copy = offsetSamples.copyOf(offsetCount)
        copy.sort()
        return copy[offsetCount / 2]
    }

    /**
     * Wall-clock milliseconds for a sensor timestamp.
     *
     * Uses the boot anchor rather than "now", so two rows written in the same tick cannot disagree
     * with each other, and so the `date` column and `time_since_start_ms` column are derived from
     * the *same* instant instead of one from the sensor and one from the writer thread.
     */
    fun wallMsForSensorNs(eventNs: Long): Long = bootWallMs + eventNs / 1_000_000L

    fun startedWallMs(): Long = startedWallMs

    fun startedElapsedNs(): Long = startedElapsedNs

    fun tzOffsetMinutes(): Int =
        TimeZone.getDefault().getOffset(startedWallMs) / 60_000

    companion object {
        private const val ONE_SECOND_NS = 1_000_000_000L
        private const val OFFSET_SAMPLE_CAP = 4096
        private const val AGREEMENT_THRESHOLD = 0.9

        /**
         * The `date` column. The sub-second separator is a **dot**, and that is a decision.
         *
         * There are three spellings in play and they do not all parse everywhere:
         *
         *  - `HH:mm:ss_SSS` -- what the IO-VNBD header advertises.
         *  - `HH:mm:ss:SSS` -- what IO-VNBD's bytes actually contain, each value additionally
         *    wrapped in literal single quotes. `truth.py::_S_DATE` only accepts this after D-086,
         *    which at the time of writing is on an unmerged branch: against `main` the colon form
         *    fails, and it fails *silently* in the sense that it raises on the first held-out
         *    sequence rather than in the app.
         *  - `HH:mm:ss.SSS` -- a dot. Accepted by the pattern **before and after** D-086.
         *
         * We emit the dot. It is the only one of the three that parses on both sides of that fix,
         * so a recording made today stays readable whichever order the branches land in. Choosing
         * the colon to look like the dataset would buy authenticity and cost compatibility.
         *
         * We also do not reproduce the dataset's wrapping quotes. `_S_DATE` tolerates them post
         * D-086; they are a defect in a file we are not writing, and copying a bug forward to look
         * authentic is how it becomes permanent.
         *
         * `tests/test_android_logger_schema.py` asserts this against the live loader.
         */
        const val DATE_PATTERN = "yyyy-MM-dd HH:mm:ss.SSS"

        fun dateFormat(): java.text.SimpleDateFormat =
            java.text.SimpleDateFormat(DATE_PATTERN, Locale.US)
    }
}

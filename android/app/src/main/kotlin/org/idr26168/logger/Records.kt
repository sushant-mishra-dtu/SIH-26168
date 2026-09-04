package org.idr26168.logger

import java.util.Locale

/**
 * The three record types that reach a file, and the formatting of each.
 *
 * Formatting lives here rather than at the call sites so that the number of decimal places is a
 * decision made once, in one place, with its reason attached. Precision is not free: a 40-minute
 * drive is 24,000 rows in the main CSV and up to 480,000 in the raw sidecar.
 */
object Records {

    // --------------------------------------------------------------------------------------
    // Main CSV -- the harness-facing file. Column order is [Channels.HEADER], exactly.
    // --------------------------------------------------------------------------------------

    /**
     * One 10 Hz row.
     *
     * Every field is nullable and a null is written as an empty cell, which is what IO-VNBD does
     * between GNSS fixes and what `io_vnbd.py` expects -- it takes distinct fixes and refuses to
     * forward-fill, because "an interpolated measurement fed back as truth is circular".
     */
    class CsvRow(
        val timeSinceStartMs: Double,
        val accel: FloatArray?,
        val gravity: FloatArray?,
        val gyro: FloatArray?,
        val magnetic: FloatArray?,
        val orientationDeg: FloatArray?,
        val fix: GnssHub.Fix?,
        val dateText: String,
    )

    /**
     * Precision, per channel, and why.
     *
     * Inertial at 6 dp: a phone accelerometer resolves ~1e-3 m/s^2 and a gyro ~1e-4 rad/s, so 6 dp
     * is three orders below the quantisation step -- enough that rounding here can never be
     * mistaken for sensor noise in an Allan plot.
     *
     * Lat/lon at 8 dp: 1e-8 deg is ~1.1 mm. GNSS accuracy is metres; the extra digits cost bytes
     * and buy nothing, but truncating below mm would put a quantisation floor under a trajectory
     * that gets differentiated.
     */
    private const val DP_INERTIAL = 6
    private const val DP_DEGREES = 8
    private const val DP_METRES = 3

    fun formatCsvRow(row: CsvRow, sb: StringBuilder) {
        // First field, so no leading comma. Every helper below prepends its own.
        appendFixedNoComma(sb, row.timeSinceStartMs, 1)

        appendTriple(sb, row.accel, DP_INERTIAL)
        appendTriple(sb, row.gravity, DP_INERTIAL)
        appendTriple(sb, row.gyro, DP_INERTIAL)
        appendTriple(sb, row.magnetic, DP_INERTIAL)
        appendTriple(sb, row.orientationDeg, DP_METRES)

        val fix = row.fix
        if (fix == null) {
            // Seven empty GNSS cells. Not zeros: a zero latitude is a place in the Gulf of Guinea
            // and it would load as one.
            repeat(7) { sb.append(',') }
        } else {
            sb.append(',')
            appendFixedNoComma(sb, fix.latDeg, DP_DEGREES)
            sb.append(',')
            appendFixedNoComma(sb, fix.lonDeg, DP_DEGREES)
            sb.append(',')
            fix.altitudeM?.let { appendFixedNoComma(sb, it, DP_METRES) }
            sb.append(',')
            fix.speedKmh?.let { appendFixedNoComma(sb, it, DP_METRES) }
            sb.append(',')
            fix.accuracyM?.let { appendFixedNoComma(sb, it, DP_METRES) }
            sb.append(',')
            fix.bearingDeg?.let { appendFixedNoComma(sb, it, DP_METRES) }
            sb.append(',')
            sb.append(fix.satsInView)
        }

        sb.append(',')
        sb.append(row.dateText)
    }

    private fun appendTriple(sb: StringBuilder, v: FloatArray?, dp: Int) {
        if (v == null) {
            repeat(3) { sb.append(',') }
            return
        }
        for (i in 0 until 3) {
            sb.append(',')
            appendFixedNoComma(sb, v[i].toDouble(), dp)
        }
    }

    private fun appendFixedNoComma(sb: StringBuilder, value: Double, dp: Int) {
        if (value.isNaN() || value.isInfinite()) return // empty cell; never "NaN" as text
        sb.append(String.format(Locale.US, "%." + dp + "f", value))
    }

    // --------------------------------------------------------------------------------------
    // Sidecar 1 -- raw inertial at full rate. Never read by the harness.
    // --------------------------------------------------------------------------------------

    /**
     * Header for the raw inertial sidecar.
     *
     * Six value columns because that is what the uncalibrated types report: `v0..v2` are the
     * uncorrected measurement and `v3..v5` are the OS bias estimate at that instant. Both halves
     * are kept. Discarding the estimate would make the file irreversible -- you could no longer
     * reconstruct what the calibrated stream would have said, and the comparison between the two
     * is the whole reason for recording uncalibrated in the first place.
     *
     * `event_ns` is the sensor's own timestamp; `arrival_ns` is `elapsedRealtimeNanos` inside the
     * callback. The difference is delivery latency plus any timebase offset, and it is the only
     * evidence available afterwards for whether a stream was batched.
     */
    val RAW_IMU_HEADER = "stream,event_ns,arrival_ns,accuracy,v0,v1,v2,v3,v4,v5"

    fun formatRawSample(s: SensorHub.RawSample, sb: StringBuilder) {
        sb.append(s.key).append(',')
        sb.append(s.eventNs).append(',')
        sb.append(s.arrivalNs).append(',')
        sb.append(s.accuracy)
        for (i in 0 until 6) {
            sb.append(',')
            if (i < s.values.size) {
                sb.append(String.format(Locale.US, "%.6f", s.values[i]))
            }
        }
    }

    // --------------------------------------------------------------------------------------
    // Sidecar 2 -- GNSS signal quality. Never read by the harness.
    // --------------------------------------------------------------------------------------

    /**
     * Constellation columns are fixed and named, not a variable-width list, so the file stays
     * rectangular and loads without a parser. The five are the ones PS 26168's receiver set can
     * actually deliver; NavIC is recorded under `other` on purpose -- `android/README.md` is
     * explicit that NavIC is a bonus and not a dependency, and giving it its own column would
     * invite someone to plot it as though it were one.
     */
    val GNSS_STATUS_HEADER =
        "arrival_ns,in_view,used_in_fix,mean_cn0_dbhz,top_cn0_dbhz,gps,glonass,galileo,beidou,qzss,other"

    fun formatSatSample(s: GnssHub.SatSample, sb: StringBuilder) {
        sb.append(s.arrivalNs).append(',')
        sb.append(s.inView).append(',')
        sb.append(s.usedInFix).append(',')
        sb.append(String.format(Locale.US, "%.2f", s.meanCn0DbHz)).append(',')
        sb.append(String.format(Locale.US, "%.2f", s.topCn0DbHz))

        var other = 0
        for ((type, count) in s.perConstellation) {
            if (type !in NAMED_CONSTELLATIONS) other += count
        }
        for (type in NAMED_CONSTELLATIONS) {
            sb.append(',')
            sb.append(s.perConstellation[type] ?: 0)
        }
        sb.append(',')
        sb.append(other)
    }

    /** In [GNSS_STATUS_HEADER] order. Anything else -- SBAS, IRNSS/NavIC, unknown -- is `other`. */
    private val NAMED_CONSTELLATIONS = listOf(
        android.location.GnssStatus.CONSTELLATION_GPS,
        android.location.GnssStatus.CONSTELLATION_GLONASS,
        android.location.GnssStatus.CONSTELLATION_GALILEO,
        android.location.GnssStatus.CONSTELLATION_BEIDOU,
        android.location.GnssStatus.CONSTELLATION_QZSS,
    )
}

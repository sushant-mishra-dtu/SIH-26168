package org.idr26168.logger

import android.content.Context
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Where a recording goes, and the sidecar that says what it is.
 *
 * The sidecar is the point of this app. `docs/IMPLEMENTATION_PLAN.md` section 4 asks seat A for
 * one thing before anything else: **the achieved sample rate and the timestamp jitter, measured on
 * each team device**, on the grounds that "the nominal rate is not the real rate". This file is
 * where those numbers land, next to the device that produced them, in a form that can be pasted
 * into a slide without being retyped from a screenshot.
 *
 * It is JSON and not a line in the CSV because it describes the *file*, not a sample, and because
 * the main CSV cannot carry an extra column without failing the harness allowlist (see [Channels]).
 */
class Session(context: Context, val startedWallMs: Long) {

    val id: String = "S-IDR-" + STEM_FORMAT.format(Date(startedWallMs)) + "-" + deviceSlug()

    /**
     * App-specific external storage when it is available, internal storage when it is not.
     *
     * `getExternalFilesDir` returns null when external storage is unmounted or in a transitional
     * state. Passing that null straight into `File(parent, child)` is legal and quietly yields a
     * *relative* path -- the recording would succeed, land somewhere in the app's working
     * directory, and be hard to find afterwards. Falling back to `filesDir` keeps the drive.
     */
    val dir: File = File(
        File(context.getExternalFilesDir(null) ?: context.filesDir, "sessions"),
        id,
    ).also { it.mkdirs() }

    val csvFile = File(dir, id + ".csv")
    val rawImuFile = File(dir, id + "_raw_imu.csv")
    val gnssStatusFile = File(dir, id + "_gnss_status.csv")
    val sidecarFile = File(dir, id + "_session.json")

    /**
     * Bytes still writable on the volume this session is being recorded to.
     *
     * `usableSpace` rather than `freeSpace`: the two differ by whatever the filesystem holds back
     * for root, and it is the usable figure that decides whether the next `write` actually
     * succeeds.
     */
    fun usableSpaceBytes(): Long = dir.usableSpace

    /**
     * Everything about a session that is knowable before a single sample arrives.
     *
     * Shared by both writes below, so the provisional sidecar and the final one cannot drift into
     * describing the same recording differently.
     */
    private fun identityJson(requestedImuHz: Double): JSONObject {
        val root = JSONObject()
        root.put("schema", SCHEMA)
        root.put("session_id", id)

        root.put(
            "device",
            JSONObject()
                .put("manufacturer", Build.MANUFACTURER)
                .put("model", Build.MODEL)
                .put("device", Build.DEVICE)
                .put("board", Build.BOARD)
                .put("hardware", Build.HARDWARE)
                .put("android_release", Build.VERSION.RELEASE)
                .put("sdk_int", Build.VERSION.SDK_INT)
                .put("fingerprint", Build.FINGERPRINT)
        )

        root.put(
            "requested",
            JSONObject()
                .put("imu_hz", requestedImuHz)
                .put("csv_row_hz", Channels.CSV_ROW_HZ)
                .put("csv_row_hz_rationale", Channels.CSV_ROW_HZ_RATIONALE)
                .put("max_report_latency_us", 0)
                .put("high_sampling_rate_sensors_declared", true)
        )

        root.put("csv_columns", JSONArray(Channels.HEADER))
        return root
    }

    /**
     * Write a sidecar **at start**, before any data exists.
     *
     * The recording is only ever stopped in one place, and that place assumes it gets to run.
     * `stopRecording()` writes the sidecar and `onDestroy` calls it -- but a low-memory kill from
     * the OS runs neither, and what survives is three CSVs in a folder with no device, no
     * requested rate and no start time attached to them. Those numbers came off *some* phone and
     * afterwards there is no way to say which, so they cannot be reported and the drive is wasted.
     *
     * A drive is expensive and a few hundred bytes at start are not, so the identity goes down
     * first and the measurements are added on top when the recording ends cleanly. Everything in
     * here is knowable before the first sample: it does not wait on the sensors.
     *
     * `status` is how a reader tells the two apart, and it is the reason this file is not simply
     * written twice. A sidecar that still says `recording` is a session that was killed, and it
     * says so rather than looking like a complete recording whose statistics happen to be missing.
     */
    fun writeProvisionalSidecar(requestedImuHz: Double, tzOffsetMinutes: Int) {
        val root = identityJson(requestedImuHz)
        root.put("status", STATUS_RECORDING)
        root.put(
            "timing",
            JSONObject()
                .put("started_wall_ms", startedWallMs)
                .put("started_wall_iso", ISO_FORMAT.format(Date(startedWallMs)))
                .put("tz_offset_minutes", tzOffsetMinutes)
        )
        root.put("files", JSONObject().put("csv", JSONObject().put("name", csvFile.name)))
        root.put(
            "warnings",
            JSONArray().put(
                "provisional sidecar written at start; if status is still \"" + STATUS_RECORDING +
                    "\" the recording did not stop cleanly and the measurements below are absent " +
                    "rather than zero"
            )
        )
        sidecarFile.writeText(root.toString(2), Charsets.UTF_8)
    }

    /**
     * Rewrite the sidecar at stop, replacing the provisional one with the measurements.
     *
     * This is the file `docs/IMPLEMENTATION_PLAN.md` section 4 is actually asking for. It is only
     * reached when the recording stopped in an orderly way; see [writeProvisionalSidecar] for what
     * happens when it does not.
     */
    fun writeSidecar(summary: Summary) {
        val root = identityJson(summary.requestedImuHz)
        root.put("status", STATUS_COMPLETE)

        root.put(
            "timing",
            JSONObject()
                .put("started_wall_ms", startedWallMs)
                .put("started_wall_iso", ISO_FORMAT.format(Date(startedWallMs)))
                .put("stopped_wall_ms", summary.stoppedWallMs)
                .put("duration_s", summary.durationS)
                .put("tz_offset_minutes", summary.tzOffsetMinutes)
                .put("sensor_timebase", summary.timebase)
                .put("sensor_arrival_offset_ns_median", summary.medianOffsetNs)
        )

        val sensors = JSONArray()
        val byKey = summary.descriptors.associateBy { it.key }
        for (s in summary.rates) {
            val d = byKey[s.label]
            sensors.put(
                JSONObject()
                    .put("stream", s.label)
                    .put("sensor_name", d?.name ?: JSONObject.NULL)
                    .put("vendor", d?.vendor ?: JSONObject.NULL)
                    .put("type", d?.type ?: JSONObject.NULL)
                    .put("resolution", d?.resolution ?: JSONObject.NULL)
                    .put("max_range", d?.maxRange ?: JSONObject.NULL)
                    .put("power_ma", d?.powerMa ?: JSONObject.NULL)
                    .put("min_delay_us", d?.minDelayUs ?: JSONObject.NULL)
                    .put("max_delay_us", d?.maxDelayUs ?: JSONObject.NULL)
                    .put("fifo_reserved_events", d?.fifoReserved ?: JSONObject.NULL)
                    .put("fifo_max_events", d?.fifoMax ?: JSONObject.NULL)
                    .put("reporting_mode", d?.reportingMode ?: JSONObject.NULL)
                    .put("requested_hz", s.requestedHz)
                    .put("events", s.events)
                    .put("span_s", s.spanS)
                    .put("achieved_hz", s.achievedHz)
                    .put(
                        "dt_ms",
                        JSONObject()
                            .put("min", s.dtMinMs)
                            .put("mean", s.dtMeanMs)
                            .put("median", s.dtMedianMs)
                            .put("p95", s.dtP95Ms)
                            .put("p99", s.dtP99Ms)
                            .put("max", s.dtMaxMs)
                            .put("stdev", s.dtStdevMs)
                            .put("histogram_bin_ms", s.binWidthMs)
                    )
                    .put("non_monotonic_stamps", s.nonMonotonic)
                    .put("gaps_over_3x_nominal", s.gapsOver3x)
                    .put("batch_arrivals", s.batchArrivals)
            )
        }
        root.put("sensors", sensors)

        summary.gnss?.let { g ->
            root.put(
                "gnss",
                JSONObject()
                    .put("fixes", g.fixes)
                    .put("mean_accuracy_m", g.meanAccuracyM)
                    .put("mean_fix_interval_s", if (g.interval.achievedHz > 0) 1.0 / g.interval.achievedHz else 0.0)
                    .put("fix_interval_p95_s", g.interval.dtP95Ms / 1000.0)
                    .put("fix_interval_max_s", g.interval.dtMaxMs / 1000.0)
                    .put("sats_in_view_last", g.satsInView)
                    .put("sats_used_in_fix_last", g.usedInFix)
                    .put("mean_cn0_dbhz_last", g.meanCn0DbHz)
            )
        }

        root.put(
            "files",
            JSONObject()
                .put("csv", JSONObject().put("name", csvFile.name).put("rows", summary.csvRows).put("dropped", summary.csvDropped).put("bytes", csvFile.length()))
                .put("raw_imu", JSONObject().put("name", rawImuFile.name).put("rows", summary.rawRows).put("dropped", summary.rawDropped).put("bytes", rawImuFile.length()))
                .put("gnss_status", JSONObject().put("name", gnssStatusFile.name).put("rows", summary.satRows).put("dropped", summary.satDropped).put("bytes", gnssStatusFile.length()))
        )

        val warnings = JSONArray()
        summary.warnings.forEach { warnings.put(it) }
        root.put("warnings", warnings)

        sidecarFile.writeText(root.toString(2), Charsets.UTF_8)
    }

    class Summary(
        val stoppedWallMs: Long,
        val durationS: Double,
        val tzOffsetMinutes: Int,
        val timebase: String,
        val medianOffsetNs: Long,
        val requestedImuHz: Double,
        val rates: List<RateStats.Snapshot>,
        val descriptors: List<SensorHub.SensorDescriptor>,
        val gnss: GnssHub.Summary?,
        val csvRows: Long,
        val csvDropped: Long,
        val rawRows: Long,
        val rawDropped: Long,
        val satRows: Long,
        val satDropped: Long,
        val warnings: List<String>,
    )

    companion object {
        const val SCHEMA = "idr-logger-session/1"

        /**
         * `status` in the sidecar. Two values, and the distinction is the point of having the
         * field: `recording` means the file was written at start and never rewritten, so the
         * session was killed; `complete` means it stopped in an orderly way and the measurements
         * in the file are the whole recording rather than the part that happened to survive.
         */
        const val STATUS_RECORDING = "recording"
        const val STATUS_COMPLETE = "complete"

        private val STEM_FORMAT = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US)
        private val ISO_FORMAT = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US)

        /** Device tag for the filename: lowercase, alphanumeric, so it survives every filesystem. */
        private fun deviceSlug(): String {
            val raw = (Build.MANUFACTURER + "-" + Build.MODEL).lowercase(Locale.US)
            val cleaned = raw.replace(Regex("[^a-z0-9]+"), "-").trim('-')
            return if (cleaned.length > 24) cleaned.substring(0, 24).trim('-') else cleaned
        }
    }
}

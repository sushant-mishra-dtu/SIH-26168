package org.idr26168.logger

/**
 * The CSV schema, and the reason it is not free.
 *
 * `eval/loaders/io_vnbd.py::_canonicalise` calls `assert_no_leakage` over **every** column in the
 * file, not over the columns it intends to use. So a column this app invents -- `accel_uncal_x`,
 * `battery_pct`, anything -- normalises to a name that is not in `ALLOWED_COLUMNS` and the loader
 * raises `LeakageError` on the whole file. The allowlist is not a filter. It is a whitelist of the
 * entire header.
 *
 * Two consequences, and they shape the whole app:
 *
 *   1. The main CSV carries these 24 columns and nothing else, in this order.
 *   2. Everything else we want to record -- uncalibrated inertial, per-satellite C/N0, raw sensor
 *      timestamps, the OS bias estimates -- goes to a **sidecar** file that the harness never
 *      reads. See [RawSink].
 *
 * Each header string below is written so that `eval/loaders/columns.py::normalise` maps it onto
 * the canonical name in the comment. The `_HEADER_ALIASES` patterns are anchored at the start of
 * the whitespace-collapsed lowercase header, so the spelling matters up to the first word boundary
 * and the parenthesised unit is then discarded.
 *
 * ASCII only, deliberately. AndroSensor ships raw 0xB0/0xB5/0xB2 bytes ("(deg)", "(uT)",
 * "(m/s^2)") and the loader reads latin-1 to survive them. Our headers say the same thing in
 * ASCII, which normalises identically and cannot be corrupted by an editor that helpfully
 * re-encodes the file to UTF-8. The file is still *written* as ISO-8859-1 so it round-trips
 * through the loader's `encoding="latin-1"` byte for byte.
 */
object Channels {

    /** Header row, in file order. */
    val HEADER: List<String> = listOf(
        "Time since start (ms)",     // -> time_since_start_ms   alias ^time since start \(ms
        "ACCELEROMETER X (m/s^2)",   // -> accel_x
        "ACCELEROMETER Y (m/s^2)",   // -> accel_y
        "ACCELEROMETER Z (m/s^2)",   // -> accel_z
        "GRAVITY X (m/s^2)",         // -> gravity_x   (no alias; generic path strips the unit)
        "GRAVITY Y (m/s^2)",         // -> gravity_y
        "GRAVITY Z (m/s^2)",         // -> gravity_z
        "GYROSCOPE X (rad/s)",       // -> gyro_yaw    see NOTE below
        "GYROSCOPE Y (rad/s)",       // -> gyro_pitch
        "GYROSCOPE Z (rad/s)",       // -> gyro_roll
        "MAGNETIC FIELD X (uT)",     // -> magnetic_x
        "MAGNETIC FIELD Y (uT)",     // -> magnetic_y
        "MAGNETIC FIELD Z (uT)",     // -> magnetic_z
        "ORIENTATION (yaw deg)",     // -> orientation_yaw   alias ^orientation \((yaw|azimuth)
        "ORIENTATION (pitch deg)",   // -> orientation_pitch
        "ORIENTATION (roll deg)",    // -> orientation_roll
        "GPS Latitude (deg)",        // -> gps_lat
        "GPS Longitude (deg)",       // -> gps_lon
        "GPS Altitude (m)",          // -> gps_altitude_m
        "GPS Speed (m/s)",           // -> gps_speed_mps     NOTE: m/s, not km/h. See [mps].
        "GPS Accuracy (m)",          // -> gps_accuracy_m
        "GPS Orientation (deg)",     // -> gps_orientation_deg
        "Satellites in range",       // -> gps_sats
        "DATE (YYYY-MO-DD HH-MI-SS_SSS)", // -> date          alias ^date\b
    )

    /**
     * NOTE on the gyro column names, because they are actively misleading and the loader says so:
     *
     * `GYROSCOPE X` normalises to `gyro_yaw`, `Y` to `gyro_pitch`, `Z` to `gyro_roll`. That is
     * AndroSensor's labelling, not a claim about axes -- `columns.py` verified on S-S1, which
     * ships in both folders, that the "Yaw/Pitch/Roll" and "X/Y/Z" spellings are byte-identical
     * columns. `gyro_yaw` is therefore **device x**, not the vertical axis.
     *
     * We emit the X/Y/Z spelling for exactly that reason: it is the one that does not invite a
     * reader to assume `gyro_yaw` is a yaw rate. The canonical name downstream is still `gyro_yaw`
     * and that is out of our hands.
     */
    const val GYRO_AXIS_NOTE = "GYROSCOPE X/Y/Z -> gyro_yaw/pitch/roll; these are device axes"

    /** Row cadence of the main CSV, in Hz. */
    const val CSV_ROW_HZ = 10

    /**
     * Why 10 and not the device maximum: `eval/loaders/io_vnbd.py` hard-codes
     * `SAMPLE_RATE_HZ = 10`, and `eval/outages/inject.py` sizes every outage window from it. A
     * 100 Hz file would load and then be windowed as though it were ten times longer. The full-rate
     * stream is not lost -- it goes to the sidecar (see [RawSink]) -- but the harness-facing file
     * is 10 Hz because that is the rate the harness was built for.
     */
    const val CSV_ROW_HZ_RATIONALE =
        "eval/loaders/io_vnbd.py SAMPLE_RATE_HZ = 10; a faster main CSV would be mis-windowed"

    const val CSV_ROW_PERIOD_MS: Long = 1000L / CSV_ROW_HZ

    /**
     * m/s as Android reports it, and m/s as the `gps_speed_mps` column is defined -- the widening
     * to `Double` is the whole of the conversion.
     *
     * There was a `* 3.6` here until D-109, and it was correct against the `GPS SPEED (Kmh)`
     * header IO-VNBD ships and wrong against the bytes behind it. D-096 measured that column at
     * 1.00x a chord-speed reference in metres per second; D-102 renamed the canonical column
     * `gps_speed_mps` and removed the matching `/ 3.6` from `_forward_reference`. Multiplying
     * here after that would write every recording 3.6x fast into a column nothing divides again.
     */
    fun mps(metresPerSecond: Float): Double = metresPerSecond.toDouble()
}

package org.idr26168.logger

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.SensorManager
import android.location.LocationManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.PowerManager
import android.os.SystemClock
import java.util.Date
import java.util.Locale

/**
 * The recorder.
 *
 * A foreground service because there is no alternative: since Android 9, a backgrounded app
 * receives no continuous sensor events at all. The persistent notification is not a courtesy, it
 * is the price of the data.
 *
 * ## Threads
 *
 * Four, and each one has a reason:
 *
 *  - **sensor** -- every `SensorEventListener` callback. Its only jobs are to update a volatile
 *    reference, feed [RateStats], and offer to a queue. It must never touch a file.
 *  - **gnss** -- `LocationListener` and `GnssStatus.Callback`. Separate from the sensor thread so
 *    a slow fix callback cannot delay an IMU sample and show up as jitter we then measure and
 *    believe.
 *  - **tick** -- the 10 Hz CSV cadence.
 *  - **writer** (one per file, inside [LineWriter]) -- formatting and I/O.
 *
 * This mirrors the structure `android/README.md` specifies for the demo app, minus the filter and
 * inference threads. Establishing it here means the demo does not have to introduce concurrency
 * and correctness at the same time.
 *
 * ## The wake lock
 *
 * A partial wake lock is held for the whole recording. Without it the CPU suspends between sensor
 * batches with the screen off, and what comes back is a stream with second-long holes that look
 * exactly like sensor dropout. Holding it costs battery and buys a stream whose gaps mean
 * something.
 */
class LoggerService : Service() {

    private lateinit var sensorThread: HandlerThread
    private lateinit var gnssThread: HandlerThread
    private lateinit var tickThread: HandlerThread
    private lateinit var sensorHandler: Handler
    private lateinit var gnssHandler: Handler
    private lateinit var tickHandler: Handler

    private var wakeLock: PowerManager.WakeLock? = null

    private var session: Session? = null
    private var clock: SessionClock? = null
    private var sensorHub: SensorHub? = null
    private var gnssHub: GnssHub? = null

    private var csvWriter: LineWriter<Records.CsvRow>? = null
    private var rawWriter: LineWriter<SensorHub.RawSample>? = null
    private var satWriter: LineWriter<GnssHub.SatSample>? = null

    private val warnings = mutableListOf<String>()
    private var requestedImuHz = DEFAULT_IMU_HZ
    private var nextTickUptimeMs = 0L
    private var running = false

    private val dateFormat = SessionClock.dateFormat()
    private val dateBuffer = Date()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopRecording()
                stopSelf()
                return START_NOT_STICKY
            }

            else -> {
                requestedImuHz = intent?.getDoubleExtra(EXTRA_IMU_HZ, DEFAULT_IMU_HZ)
                    ?: DEFAULT_IMU_HZ
                startRecording()
            }
        }
        // NOT_STICKY on purpose. If the system kills this service mid-drive, restarting it would
        // silently open a *second* session file with a gap in front of it, and the gap would be
        // invisible in the data. A recording that stops is a recording you know about.
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        stopRecording()
        super.onDestroy()
    }

    // ------------------------------------------------------------------------------------------

    private fun startRecording() {
        if (running) return
        running = true
        warnings.clear()

        startForegroundWithNotification()
        acquireWakeLock()

        val startedWallMs = System.currentTimeMillis()
        val sess = Session(this, startedWallMs)
        val clk = SessionClock()
        session = sess
        clock = clk

        sensorThread = HandlerThread("idr-sensor", android.os.Process.THREAD_PRIORITY_URGENT_AUDIO)
            .also { it.start() }
        gnssThread = HandlerThread("idr-gnss").also { it.start() }
        tickThread = HandlerThread("idr-tick", android.os.Process.THREAD_PRIORITY_FOREGROUND)
            .also { it.start() }
        sensorHandler = Handler(sensorThread.looper)
        gnssHandler = Handler(gnssThread.looper)
        tickHandler = Handler(tickThread.looper)

        csvWriter = LineWriter(
            file = sess.csvFile,
            header = Channels.HEADER.joinToString(","),
            capacity = CSV_QUEUE,
            format = Records::formatCsvRow,
        ).also { it.start() }

        rawWriter = LineWriter(
            file = sess.rawImuFile,
            header = Records.RAW_IMU_HEADER,
            capacity = RAW_QUEUE,
            format = Records::formatRawSample,
        ).also { it.start() }

        satWriter = LineWriter(
            file = sess.gnssStatusFile,
            header = Records.GNSS_STATUS_HEADER,
            capacity = SAT_QUEUE,
            format = Records::formatSatSample,
        ).also { it.start() }

        val hub = SensorHub(
            sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager,
            clock = clk,
            requestedHz = requestedImuHz,
            onRaw = { rawWriter?.offer(it) },
        )
        sensorHub = hub
        warnings += hub.start(sensorHandler)

        val gnss = GnssHub(
            locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager,
            onSatSample = { satWriter?.offer(it) },
        )
        gnssHub = gnss
        try {
            warnings += gnss.start(gnssHandler)
        } catch (e: SecurityException) {
            warnings += "location permission missing: no GNSS in this recording (" + e.message + ")"
        }

        nextTickUptimeMs = SystemClock.uptimeMillis() + Channels.CSV_ROW_PERIOD_MS
        tickHandler.postAtTime(tickRunnable, nextTickUptimeMs)
    }

    private fun stopRecording() {
        if (!running) return
        running = false

        tickHandler.removeCallbacksAndMessages(null)
        sensorHub?.stop()
        try {
            gnssHub?.stop()
        } catch (e: SecurityException) {
            warnings += "could not unregister GNSS: " + e.message
        }

        // Order matters: stop producing, then drain, then describe. A sidecar written before the
        // writers drain reports a row count the file does not have.
        csvWriter?.stop()
        rawWriter?.stop()
        satWriter?.stop()

        writeSidecar()

        sensorThread.quitSafely()
        gnssThread.quitSafely()
        tickThread.quitSafely()

        releaseWakeLock()
        stopForegroundCompat()
        LoggerState.reset()

        session = null
        clock = null
        sensorHub = null
        gnssHub = null
        csvWriter = null
        rawWriter = null
        satWriter = null
    }

    // ------------------------------------------------------------------------------------------

    private val tickRunnable = object : Runnable {
        override fun run() {
            if (!running) return
            try {
                writeRow()
            } finally {
                // Fixed-schedule, not fixed-delay: each tick is scheduled from the *previous
                // target*, so a late tick does not push every later one later. The CSV cadence is
                // the app's own clock and it must not inherit the scheduler's drift -- although
                // the row's timestamp comes from the accelerometer either way (D-013), so a late
                // tick costs a sample, never a wrong time.
                nextTickUptimeMs += Channels.CSV_ROW_PERIOD_MS
                val now = SystemClock.uptimeMillis()
                if (nextTickUptimeMs <= now) nextTickUptimeMs = now + Channels.CSV_ROW_PERIOD_MS
                tickHandler.postAtTime(this, nextTickUptimeMs)
            }
        }
    }

    private fun writeRow() {
        val hub = sensorHub ?: return
        val clk = clock ?: return
        val snap = hub.snapshot()

        // No accelerometer event yet means no row clock. Writing a row timed off the tick instead
        // would be exactly the nominal-dt substitution D-013 exists to forbid.
        if (!snap.hasClock()) return

        // The fix is repeated across rows until the receiver produces a new one. That is what
        // IO-VNBD does and what the loader expects -- it takes fixes as position changes, so a
        // repeated row is not counted twice and nothing is forward-filled on our side.
        val fix = gnssHub?.snapshot()

        dateBuffer.time = clk.wallMsForSensorNs(snap.accelEventNs)
        val row = Records.CsvRow(
            timeSinceStartMs = (snap.accelEventNs - snap.firstAccelEventNs) / 1e6,
            accel = snap.accel,
            gravity = snap.gravity,
            gyro = snap.gyro,
            magnetic = snap.magnetic,
            orientationDeg = snap.orientationDeg,
            fix = fix,
            dateText = dateFormat.format(dateBuffer),
        )
        csvWriter?.offer(row)

        publishSnapshot()
    }

    private fun publishSnapshot() {
        val sess = session ?: return
        val clk = clock ?: return
        val hub = sensorHub ?: return
        val nowNs = SystemClock.elapsedRealtimeNanos()

        val streams = hub.stats().map {
            LoggerState.StreamReadout(
                label = it.label,
                requestedHz = it.requestedHz,
                achievedHz = it.achievedHz,
                dtMedianMs = it.dtMedianMs,
                dtP95Ms = it.dtP95Ms,
                dtStdevMs = it.dtStdevMs,
                events = it.events,
                nonMonotonic = it.nonMonotonic,
                batchArrivals = it.batchArrivals,
            )
        }

        val fix = gnssHub?.snapshot()
        val gnssSummary = gnssHub?.summary()
        val gnssReadout = if (gnssSummary == null) null else LoggerState.GnssReadout(
            fixes = gnssSummary.fixes,
            ageS = fix?.ageS(nowNs) ?: Double.NaN,
            accuracyM = fix?.accuracyM ?: Double.NaN,
            satsInView = gnssSummary.satsInView,
            usedInFix = gnssSummary.usedInFix,
            meanCn0DbHz = gnssSummary.meanCn0DbHz,
        )

        LoggerState.publish(
            LoggerState.Snapshot(
                running = true,
                sessionId = sess.id,
                sessionDir = sess.dir.absolutePath,
                elapsedS = (nowNs - clk.startedElapsedNs()) / 1e9,
                csvRows = csvWriter?.written() ?: 0,
                csvDropped = csvWriter?.dropped() ?: 0,
                rawRows = rawWriter?.written() ?: 0,
                rawDropped = rawWriter?.dropped() ?: 0,
                bytesOnDisk = (csvWriter?.sizeBytes() ?: 0) + (rawWriter?.sizeBytes() ?: 0) +
                    (satWriter?.sizeBytes() ?: 0),
                streams = streams,
                gnss = gnssReadout,
                timebase = clk.timebase().name,
                warnings = warnings + liveWarnings(streams),
            )
        )
    }

    /**
     * Warnings that can only be known from measurement, recomputed each tick.
     *
     * The rate-limit case is the one `android/README.md` calls out: if the user has disabled
     * microphone access with the device-level toggle, motion sensors are rate-limited **whatever**
     * permissions the app holds, and the recording quietly becomes useless. There is no public API
     * that reports this to a normal app -- `SensorPrivacyManager` is not ours to call -- so the
     * only honest detector is the achieved rate itself. Which is why the app measures it live and
     * shows it on the front screen rather than filing it in a report nobody reads until afterwards.
     */
    private fun liveWarnings(streams: List<LoggerState.StreamReadout>): List<String> {
        val out = mutableListOf<String>()
        val accel = streams.firstOrNull { it.label == "accelerometer" } ?: return out
        if (accel.events < RATE_WARNING_MIN_EVENTS) return out

        val ratio = accel.achievedHz / accel.requestedHz
        if (ratio < RATE_WARNING_RATIO) {
            out += String.format(
                Locale.US,
                "accelerometer is delivering %.1f Hz of the %.1f Hz requested (%.0f%%). " +
                    "Check the device microphone toggle: with it off, motion sensors are " +
                    "rate-limited regardless of permissions. Thermal throttling looks the same.",
                accel.achievedHz, accel.requestedHz, ratio * 100.0,
            )
        }
        if (accel.requestedHz > HIGH_RATE_CAP_HZ && accel.achievedHz < HIGH_RATE_CAP_HZ * 1.05) {
            out += "requested above 200 Hz but achieving about 200 Hz: the API 31 cap is in " +
                "force, so HIGH_SAMPLING_RATE_SENSORS is not taking effect"
        }
        if (accel.nonMonotonic > 0) {
            out += accel.nonMonotonic.toString() + " non-monotonic accelerometer timestamps"
        }
        return out
    }

    private fun writeSidecar() {
        val sess = session ?: return
        val clk = clock ?: return
        val hub = sensorHub ?: return
        val stoppedWallMs = System.currentTimeMillis()
        try {
            sess.writeSidecar(
                Session.Summary(
                    stoppedWallMs = stoppedWallMs,
                    durationS = (stoppedWallMs - clk.startedWallMs()) / 1000.0,
                    tzOffsetMinutes = clk.tzOffsetMinutes(),
                    timebase = clk.timebase().name,
                    medianOffsetNs = clk.medianOffsetNs(),
                    requestedImuHz = requestedImuHz,
                    rates = hub.stats(),
                    descriptors = hub.descriptors(),
                    gnss = gnssHub?.summary(),
                    csvRows = csvWriter?.written() ?: 0,
                    csvDropped = csvWriter?.dropped() ?: 0,
                    rawRows = rawWriter?.written() ?: 0,
                    rawDropped = rawWriter?.dropped() ?: 0,
                    satRows = satWriter?.written() ?: 0,
                    satDropped = satWriter?.dropped() ?: 0,
                    warnings = warnings.toList(),
                )
            )
        } catch (e: Exception) {
            // A failed sidecar must not take the recording with it: the CSV is already on disk and
            // is the thing that cost a drive to collect.
            android.util.Log.e(TAG, "sidecar write failed for " + sess.id, e)
        }
    }

    // ------------------------------------------------------------------------------------------

    private fun startForegroundWithNotification() {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.channel_name),
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = getString(R.string.channel_description)
            setShowBadge(false)
        }
        manager.createNotificationChannel(channel)

        val open = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )

        val notification: Notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText("Recording sensors and GNSS")
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setOngoing(true)
            .setContentIntent(open)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun stopForegroundCompat() {
        // minSdk is 26, so STOP_FOREGROUND_REMOVE (API 24) needs no version guard.
        stopForeground(STOP_FOREGROUND_REMOVE)
    }

    private fun acquireWakeLock() {
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, WAKE_TAG).apply {
            setReferenceCounted(false)
            acquire(MAX_RECORDING_MS)
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
    }

    companion object {
        private const val TAG = "IdrLogger"

        const val ACTION_START = "org.idr26168.logger.START"
        const val ACTION_STOP = "org.idr26168.logger.STOP"
        const val EXTRA_IMU_HZ = "imu_hz"

        /**
         * 100 Hz by default.
         *
         * Not 10 Hz: the main CSV is decimated to 10 Hz for the harness, but the raw sidecar is
         * the only place an Allan-variance run on *our* hardware can come from, and 10 Hz cannot
         * see the short-tau end of it.
         *
         * Not 200+ Hz by default either: above 200 Hz the API 31 cap applies unless
         * HIGH_SAMPLING_RATE_SENSORS takes effect, and sustained high-rate sensing plus the
         * writers heats the SoC until it throttles -- which shows up as a falling achieved rate
         * partway through a drive, i.e. as the exact measurement this app exists to make, ruined.
         * Raise it deliberately, per device, and read the number back from the sidecar.
         */
        const val DEFAULT_IMU_HZ = 100.0

        private const val HIGH_RATE_CAP_HZ = 200.0
        private const val RATE_WARNING_RATIO = 0.8
        private const val RATE_WARNING_MIN_EVENTS = 200L

        private const val CHANNEL_ID = "recording"
        private const val NOTIFICATION_ID = 1
        private const val WAKE_TAG = "idr-logger:recording"

        /** Wake-lock ceiling. Four hours is longer than any drive we plan and short of forever. */
        private const val MAX_RECORDING_MS = 4L * 60L * 60L * 1000L

        private const val CSV_QUEUE = 4096
        private const val RAW_QUEUE = 16384
        private const val SAT_QUEUE = 1024
    }
}

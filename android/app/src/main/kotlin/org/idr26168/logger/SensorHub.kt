package org.idr26168.logger

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.SystemClock
import java.util.Locale

/**
 * Sensor registration, the latest-value snapshot the CSV tick reads, and the per-stream rate
 * statistics.
 *
 * ## Calibrated *and* uncalibrated, not one or the other
 *
 * `android/README.md` says to use `TYPE_ACCELEROMETER_UNCALIBRATED` / `TYPE_GYROSCOPE_UNCALIBRATED`,
 * because the calibrated types subtract an OS bias estimate that the filter is also estimating and
 * the two then fight over the same state. That is right, and it is what the *filter* should
 * consume.
 *
 * But D-085 established what IO-VNBD actually contains: AndroSensor's `TYPE_ACCELEROMETER` plus a
 * separate `TYPE_GRAVITY` channel -- calibrated, gravity included, not a raw IMU log. A file whose
 * `accel_*` columns held uncalibrated values would load through the same loader and mean a
 * different physical quantity than every sequence it gets compared against.
 *
 * So both are recorded and they are kept apart:
 *  - **main CSV** -- calibrated accel, gravity, gyro, magnetometer. Same quantities as IO-VNBD,
 *    so a drive of ours is comparable with a drive of theirs.
 *  - **sidecar** -- uncalibrated accel and gyro *with the OS bias estimates alongside* (the
 *    uncalibrated types report both: values[0..2] uncorrected, values[3..5] the estimate). Keeping
 *    the estimate is what makes the pair reversible in either direction after the fact.
 *
 * ## No batching
 *
 * Every registration passes `maxReportLatencyUs = 0`. A FIFO that batches is cheaper on power and
 * delivers timestamps that are still correct, but it reorders and it adds latency measured in
 * whole seconds -- and afterwards the app cannot tell whether a gap was a batch or a dropped
 * window. [RateStats] counts batch arrivals anyway, because "we asked for 0" is not the same as
 * "we got 0".
 */
class SensorHub(
    private val sensorManager: SensorManager,
    private val clock: SessionClock,
    private val requestedHz: Double,
    private val onRaw: (RawSample) -> Unit,
) : SensorEventListener {

    /** One registered stream: the sensor, what we asked for, and what we got. */
    class Stream(
        val key: String,
        val sensor: Sensor,
        val stats: RateStats,
    )

    private val streams = LinkedHashMap<Int, Stream>()

    // Latest value per channel. Written on the sensor thread, read on the CSV tick thread.
    // Volatile array *references*, swapped whole, so a reader never sees a half-updated triple.
    @Volatile private var accel: FloatArray? = null
    @Volatile private var gravity: FloatArray? = null
    @Volatile private var gyro: FloatArray? = null
    @Volatile private var magnetic: FloatArray? = null
    @Volatile private var orientationDeg: FloatArray? = null

    /** Timestamp of the most recent accelerometer event. The CSV row's clock, per D-013. */
    @Volatile private var accelEventNs: Long = 0
    @Volatile private var firstAccelEventNs: Long = 0

    private val rotationMatrix = FloatArray(9)
    private val orientationRad = FloatArray(3)

    fun start(handler: Handler): List<String> {
        val warnings = mutableListOf<String>()
        val periodUs = (1_000_000.0 / requestedHz).toInt()

        for ((key, type) in WANTED) {
            val sensor = sensorManager.getDefaultSensor(type)
            if (sensor == null) {
                warnings += "no sensor for " + key + " (type " + type + ") on this device"
                continue
            }
            // minDelay is the hardware floor in us. Asking for faster than it is not an error and
            // not honoured; recording the mismatch is the point of the exercise.
            if (sensor.minDelay > 0 && periodUs < sensor.minDelay) {
                val maxHz = 1_000_000.0 / sensor.minDelay
                warnings += key + ": asked " + fmt(requestedHz) + " Hz, hardware floor is " +
                    fmt(maxHz) + " Hz (minDelay " + sensor.minDelay + " us)"
            }
            val ok = sensorManager.registerListener(this, sensor, periodUs, 0, handler)
            if (!ok) {
                warnings += key + ": registerListener returned false"
                continue
            }
            streams[type] = Stream(key, sensor, RateStats(key, requestedHz))
        }
        return warnings
    }

    fun stop() {
        sensorManager.unregisterListener(this)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Deliberately empty. Accuracy is recorded per-sample in the sidecar, where it can be
        // correlated with the data; a callback that only says "it changed" cannot be.
    }

    override fun onSensorChanged(event: SensorEvent) {
        val arrivalElapsed = SystemClock.elapsedRealtimeNanos()
        val arrivalUptime = SystemClock.uptimeMillis() * 1_000_000L
        val ts = event.timestamp

        streams[event.sensor.type]?.stats?.add(ts, arrivalElapsed)
        clock.probe(ts, arrivalElapsed, arrivalUptime)

        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                accel = event.values.copyOf(3)
                if (firstAccelEventNs == 0L) firstAccelEventNs = ts
                accelEventNs = ts
            }

            Sensor.TYPE_GRAVITY -> gravity = event.values.copyOf(3)
            Sensor.TYPE_GYROSCOPE -> gyro = event.values.copyOf(3)
            Sensor.TYPE_MAGNETIC_FIELD -> magnetic = event.values.copyOf(3)

            Sensor.TYPE_ROTATION_VECTOR -> {
                SensorManager.getRotationMatrixFromVector(rotationMatrix, event.values)
                SensorManager.getOrientation(rotationMatrix, orientationRad)
                orientationDeg = floatArrayOf(
                    Math.toDegrees(orientationRad[0].toDouble()).toFloat(),
                    Math.toDegrees(orientationRad[1].toDouble()).toFloat(),
                    Math.toDegrees(orientationRad[2].toDouble()).toFloat(),
                )
            }

            // Uncalibrated streams never touch the main CSV. They go straight to the sidecar at
            // full rate, carrying the OS bias estimate that arrived with them.
            Sensor.TYPE_ACCELEROMETER_UNCALIBRATED,
            Sensor.TYPE_GYROSCOPE_UNCALIBRATED,
            Sensor.TYPE_MAGNETIC_FIELD_UNCALIBRATED,
            -> onRaw(
                RawSample(
                    key = streams[event.sensor.type]?.key ?: ("type_" + event.sensor.type),
                    eventNs = ts,
                    arrivalNs = arrivalElapsed,
                    accuracy = event.accuracy,
                    values = event.values.copyOf(),
                )
            )
        }
    }

    /** Latest value of every main-CSV channel, taken as one consistent set. */
    fun snapshot(): Snapshot = Snapshot(
        accelEventNs = accelEventNs,
        firstAccelEventNs = firstAccelEventNs,
        accel = accel,
        gravity = gravity,
        gyro = gyro,
        magnetic = magnetic,
        orientationDeg = orientationDeg,
    )

    fun stats(): List<RateStats.Snapshot> = streams.values.map { it.stats.snapshot() }

    fun descriptors(): List<SensorDescriptor> = streams.values.map {
        SensorDescriptor(
            key = it.key,
            name = it.sensor.name,
            vendor = it.sensor.vendor,
            version = it.sensor.version,
            type = it.sensor.type,
            resolution = it.sensor.resolution,
            maxRange = it.sensor.maximumRange,
            powerMa = it.sensor.power,
            minDelayUs = it.sensor.minDelay,
            maxDelayUs = it.sensor.maxDelay,
            fifoReserved = it.sensor.fifoReservedEventCount,
            fifoMax = it.sensor.fifoMaxEventCount,
            reportingMode = it.sensor.reportingMode,
        )
    }

    class Snapshot(
        val accelEventNs: Long,
        val firstAccelEventNs: Long,
        val accel: FloatArray?,
        val gravity: FloatArray?,
        val gyro: FloatArray?,
        val magnetic: FloatArray?,
        val orientationDeg: FloatArray?,
    ) {
        /** True once the row clock exists. Before the first accel event there is no row to write. */
        fun hasClock(): Boolean = accelEventNs != 0L
    }

    class RawSample(
        val key: String,
        val eventNs: Long,
        val arrivalNs: Long,
        val accuracy: Int,
        val values: FloatArray,
    )

    data class SensorDescriptor(
        val key: String,
        val name: String,
        val vendor: String,
        val version: Int,
        val type: Int,
        val resolution: Float,
        val maxRange: Float,
        val powerMa: Float,
        val minDelayUs: Int,
        val maxDelayUs: Int,
        val fifoReserved: Int,
        val fifoMax: Int,
        val reportingMode: Int,
    )

    companion object {
        /** Registration order is the order they appear in the sidecar. */
        private val WANTED: List<Pair<String, Int>> = listOf(
            "accelerometer" to Sensor.TYPE_ACCELEROMETER,
            "gravity" to Sensor.TYPE_GRAVITY,
            "gyroscope" to Sensor.TYPE_GYROSCOPE,
            "magnetic_field" to Sensor.TYPE_MAGNETIC_FIELD,
            "rotation_vector" to Sensor.TYPE_ROTATION_VECTOR,
            "accelerometer_uncalibrated" to Sensor.TYPE_ACCELEROMETER_UNCALIBRATED,
            "gyroscope_uncalibrated" to Sensor.TYPE_GYROSCOPE_UNCALIBRATED,
            "magnetic_field_uncalibrated" to Sensor.TYPE_MAGNETIC_FIELD_UNCALIBRATED,
        )

        private fun fmt(v: Double) = String.format(Locale.US, "%.1f", v)
    }
}

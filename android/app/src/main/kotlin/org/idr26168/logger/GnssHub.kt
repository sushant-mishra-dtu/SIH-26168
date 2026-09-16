package org.idr26168.logger

import android.annotation.SuppressLint
import android.location.GnssStatus
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Handler
import android.os.SystemClock

/**
 * GNSS fixes and the per-satellite signal quality that says whether to believe them.
 *
 * Two deliberate choices.
 *
 * **Raw `LocationManager`, not the fused provider.** The fused provider blends in sensor-derived
 * dead reckoning of its own. Logging it would mean recording a position that already contains
 * somebody else's filter, and then evaluating our filter against it. `GPS_PROVIDER` at
 * `minTime = 0, minDistance = 0` gives what the receiver produced.
 *
 * **`GnssStatus` is recorded even though the main CSV has nowhere to put it.** The allowlist has
 * one GNSS quality column, `gps_sats` (satellites in range). Per-satellite C/N0 goes to the
 * sidecar, because it is the input to the outage-detection argument in `android/README.md`: the OS
 * keeps reporting a "good" coasted fix for a while after real signal loss, and C/N0 collapsing
 * across the constellation is the earliest honest evidence that the fix has gone stale.
 *
 * This class detects nothing. It records. Gating is the filter's job and belongs behind the chi^2
 * test, not in a logger.
 */
class GnssHub(
    private val locationManager: LocationManager,
    private val onSatSample: (SatSample) -> Unit,
) : LocationListener {

    @Volatile private var latest: Location? = null
    @Volatile private var latestSats: Int = 0
    @Volatile private var latestUsedInFix: Int = 0
    @Volatile private var latestTopCn0: Float = 0f
    @Volatile private var latestMeanCn0: Float = 0f

    private val fixStats = RateStats("gnss_fix", 1.0)
    private var fixCount: Long = 0
    private var accuracySumM: Double = 0.0

    private val statusCallback = object : GnssStatus.Callback() {
        override fun onSatelliteStatusChanged(status: GnssStatus) {
            val arrival = SystemClock.elapsedRealtimeNanos()
            val n = status.satelliteCount
            var used = 0
            var sum = 0f
            var top = 0f
            val perConstellation = HashMap<Int, Int>()
            for (i in 0 until n) {
                val cn0 = status.getCn0DbHz(i)
                sum += cn0
                if (cn0 > top) top = cn0
                if (status.usedInFix(i)) used++
                val c = status.getConstellationType(i)
                perConstellation[c] = (perConstellation[c] ?: 0) + 1
            }
            latestSats = n
            latestUsedInFix = used
            latestTopCn0 = top
            latestMeanCn0 = if (n > 0) sum / n else 0f
            onSatSample(
                SatSample(
                    arrivalNs = arrival,
                    inView = n,
                    usedInFix = used,
                    meanCn0DbHz = latestMeanCn0,
                    topCn0DbHz = top,
                    perConstellation = perConstellation,
                )
            )
        }
    }

    /**
     * Caller checks ACCESS_FINE_LOCATION before this runs; a SecurityException here means the
     * permission was revoked mid-drive, which is a recording that must stop rather than continue
     * without GNSS and look complete.
     */
    @SuppressLint("MissingPermission")
    fun start(handler: Handler): List<String> {
        val warnings = mutableListOf<String>()
        if (!locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
            warnings += "GPS provider is disabled in system settings; there will be no fixes"
        }
        locationManager.requestLocationUpdates(
            LocationManager.GPS_PROVIDER,
            0L,
            0f,
            this,
            handler.looper,
        )
        val registered = locationManager.registerGnssStatusCallback(statusCallback, handler)
        if (!registered) warnings += "registerGnssStatusCallback returned false; no C/N0 recorded"
        return warnings
    }

    @SuppressLint("MissingPermission")
    fun stop() {
        locationManager.removeUpdates(this)
        locationManager.unregisterGnssStatusCallback(statusCallback)
    }

    override fun onLocationChanged(location: Location) {
        // elapsedRealtimeNanos, not getTime(): it shares a base with SensorEvent.timestamp on
        // every device where the sensor base is elapsed-realtime, so the two streams can be put on
        // one clock without going through UTC and back.
        fixStats.add(location.elapsedRealtimeNanos, SystemClock.elapsedRealtimeNanos())
        fixCount++
        if (location.hasAccuracy()) accuracySumM += location.accuracy.toDouble()
        latest = location
    }

    @Deprecated("Required by the LocationListener interface below API 30.")
    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit

    override fun onProviderEnabled(provider: String) = Unit

    override fun onProviderDisabled(provider: String) = Unit

    /** What the CSV writer holds between fixes. See [Fix.ageS] for why the age matters. */
    fun snapshot(): Fix? {
        val loc = latest ?: return null
        return Fix(
            latDeg = loc.latitude,
            lonDeg = loc.longitude,
            altitudeM = if (loc.hasAltitude()) loc.altitude else null,
            speedMps = if (loc.hasSpeed()) Channels.mps(loc.speed) else null,
            accuracyM = if (loc.hasAccuracy()) loc.accuracy.toDouble() else null,
            bearingDeg = if (loc.hasBearing()) loc.bearing.toDouble() else null,
            satsInView = latestSats,
            usedInFix = latestUsedInFix,
            meanCn0DbHz = latestMeanCn0,
            topCn0DbHz = latestTopCn0,
            elapsedRealtimeNs = loc.elapsedRealtimeNanos,
        )
    }

    fun summary(): Summary = Summary(
        fixes = fixCount,
        meanAccuracyM = if (fixCount > 0) accuracySumM / fixCount else 0.0,
        interval = fixStats.snapshot(),
        satsInView = latestSats,
        usedInFix = latestUsedInFix,
        meanCn0DbHz = latestMeanCn0,
    )

    class Fix(
        val latDeg: Double,
        val lonDeg: Double,
        val altitudeM: Double?,
        val speedMps: Double?,
        val accuracyM: Double?,
        val bearingDeg: Double?,
        val satsInView: Int,
        val usedInFix: Int,
        val meanCn0DbHz: Float,
        val topCn0DbHz: Float,
        val elapsedRealtimeNs: Long,
    ) {
        /**
         * Seconds since the receiver produced this fix.
         *
         * The main CSV repeats the last fix across the 10 Hz rows between updates, which is what
         * IO-VNBD does and what `io_vnbd.py` expects -- it deduplicates on position change and
         * refuses to forward-fill. The age is not a CSV column, so it is displayed live and
         * written to the sidecar instead: a fix repeated for 40 s and a fix repeated for 0.4 s
         * look identical in the file.
         */
        fun ageS(nowNs: Long): Double = (nowNs - elapsedRealtimeNs) / 1e9
    }

    class SatSample(
        val arrivalNs: Long,
        val inView: Int,
        val usedInFix: Int,
        val meanCn0DbHz: Float,
        val topCn0DbHz: Float,
        val perConstellation: Map<Int, Int>,
    )

    data class Summary(
        val fixes: Long,
        val meanAccuracyM: Double,
        val interval: RateStats.Snapshot,
        val satsInView: Int,
        val usedInFix: Int,
        val meanCn0DbHz: Float,
    )
}

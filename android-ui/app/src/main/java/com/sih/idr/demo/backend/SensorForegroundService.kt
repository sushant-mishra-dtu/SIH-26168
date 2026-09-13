package com.sih.idr.demo.backend

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.location.GnssStatus
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.os.SystemClock
import android.util.Log
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.sih.idr.demo.backend.routing.RouteTracker
import com.sih.idr.demo.backend.tunnel.FixVerdict
import com.sih.idr.demo.backend.tunnel.TunnelAssetLoader
import com.sih.idr.demo.backend.tunnel.TunnelFsm
import com.sih.idr.demo.backend.tunnel.TunnelFsmConfig
import com.sih.idr.demo.backend.tunnel.TunnelGeometry
import com.sih.idr.demo.backend.tunnel.TunnelOverride
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.backend.tunnel.portalDistanceM

class SensorForegroundService : Service(), SensorEventListener, LocationListener {
    private lateinit var sensorManager: SensorManager
    private lateinit var locationManager: LocationManager
    private var lastTimestampNs = 0L
    private var sampleCount = 0
    private var rateWindowStartNs = 0L
    private val estimator = LocalNavigationEstimator()

    // The autonomous tunnel machine (D-126). Every signal it consumes is a measurement this
    // service already receives or registers below; its state is pushed into the estimator after
    // each update and every transition is logged with its trigger.
    // Calibrated for device GNSS reception (D-116): 2.5s timeout prevents 1 Hz GPS scheduling
    // jitter false alarms; 24 dB-Hz healthy threshold accommodates urban & desk tracking.
    private val fsm = TunnelFsm(
        config = TunnelFsmConfig(
            cn0HealthyDbHz = 24f,
            cn0SuspectDbHz = 20f,
            cn0LostDbHz = 16f,
            gnssTimeoutMs = 2_500L,
            statusFreshMs = 3_500L
        ),
        startMs = SystemClock.elapsedRealtime()
    )
    // Tunnel map-based geometry loaded from bundled asset (D-126).
    private var tunnelGeometry = TunnelGeometry(emptyList())
    private var syncedTunnelState = TunnelState.GNSS_HEALTHY
    private var satelliteCount = 0
    private var currentRate = 0f
    private var currentJitter = 0f
    private var lastUiPublishMs = 0L

    private val gnssCallback = object : GnssStatus.Callback() {
        override fun onSatelliteStatusChanged(status: GnssStatus) {
            val used = (0 until status.satelliteCount).count { status.usedInFix(it) }
            val visible = (0 until status.satelliteCount).count { status.getCn0DbHz(it) > 12f }
            satelliteCount = if (used > 0) used else visible
            if (satelliteCount >= 3) {
                estimator.notifyGnssHeartbeat()
            }
            // Tunnel doc section 1.1.A: the mean C/N0 of the best four tracked satellites.
            val top4 = (0 until status.satelliteCount)
                .map { status.getCn0DbHz(it) }
                .filter { it > 0f }
                .sortedDescending()
                .take(4)
            val cn0Top4 = if (top4.isEmpty()) null else top4.average().toFloat()
            val now = SystemClock.elapsedRealtime()
            fsm.onGnssStatus(now, used, cn0Top4)
            syncTunnelState(now)
            TelemetryStore.update {
                it.copy(
                    satellites = satelliteCount,
                    cn0Top4DbHz = cn0Top4,
                    tunnelState = fsm.state,
                    tunnelTrigger = fsm.lastTransition?.trigger,
                    tunnelModeActive = fsm.state.suppressesGnss
                )
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        activeInstance = this
        tunnelGeometry = TunnelAssetLoader.load(assets)
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, notification())
        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(LOCATION_SERVICE) as LocationManager

        val accel = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER_UNCALIBRATED)
            ?: sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        val gyro = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE_UNCALIBRATED)
            ?: sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        val rotVector = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
        // Tunnel machine inputs (section 1.1.C and 1.1.D). Both are optional hardware: a phone
        // without them simply never fires those triggers, and the telemetry shows null.
        val light = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)
        val pressure = sensorManager.getDefaultSensor(Sensor.TYPE_PRESSURE)

        accel?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }
        gyro?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }
        rotVector?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }
        light?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL) }
        pressure?.let { sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }

        TelemetryStore.update {
            it.copy(running = true, accelAvailable = accel != null, gyroAvailable = gyro != null)
        }
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            val lastFused = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                try { locationManager.getLastKnownLocation(LocationManager.FUSED_PROVIDER) } catch (e: Exception) { null }
            } else null
            val lastGps = try { locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER) } catch (e: Exception) { null }
            val lastNet = try { locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER) } catch (e: Exception) { null }
            val initialLoc = lastFused ?: lastGps ?: lastNet
            initialLoc?.let { loc ->
                val now = SystemClock.elapsedRealtime()
                val estimate = estimator.onLocation(loc)
                fsm.onGnssFix(now, estimate.lastFixVerdict ?: FixVerdict.ACCEPTED)
                applyEstimate(estimate, force = true)
            }
            // Continuous periodic updates with minDistance = 0f to prevent disconnects when stopped
            try {
                locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0.0f, this)
            } catch (e: Exception) {}
            try {
                locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 2000L, 0.0f, this)
            } catch (e: Exception) {}
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                try {
                    if (locationManager.allProviders.contains(LocationManager.FUSED_PROVIDER)) {
                        locationManager.requestLocationUpdates(LocationManager.FUSED_PROVIDER, 1000L, 0.0f, this)
                    }
                } catch (e: Exception) {}
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                locationManager.registerGnssStatusCallback(gnssCallback, null)
            }
        }
    }

    override fun onSensorChanged(event: SensorEvent) {
        when (event.sensor.type) {
            Sensor.TYPE_GYROSCOPE_UNCALIBRATED, Sensor.TYPE_GYROSCOPE -> {
                val now = event.timestamp
                if (rateWindowStartNs == 0L) rateWindowStartNs = now
                sampleCount++
                val elapsedNs = now - rateWindowStartNs
                currentRate = if (elapsedNs > 0) sampleCount * 1_000_000_000f / elapsedNs else 0f
                currentJitter = if (lastTimestampNs == 0L) {
                    0f
                } else {
                    kotlin.math.abs((now - lastTimestampNs) / 1_000_000f - REQUESTED_PERIOD_US / 1000f)
                }
                lastTimestampNs = now
                val estimate = estimator.onGyro(event.values[2], now)
                applyEstimate(estimate)
            }
            Sensor.TYPE_ACCELEROMETER_UNCALIBRATED, Sensor.TYPE_ACCELEROMETER -> {
                val estimate = estimator.onAccelerometer(event.values[0], event.values[1], event.values[2], event.timestamp)
                applyEstimate(estimate)
            }
            Sensor.TYPE_LIGHT -> {
                val now = SystemClock.elapsedRealtime()
                fsm.onLight(now, event.values[0])
                syncTunnelState(now)
                TelemetryStore.update { it.copy(ambientLux = event.values[0]) }
            }
            Sensor.TYPE_PRESSURE -> {
                val now = SystemClock.elapsedRealtime()
                fsm.onPressure(now, event.values[0])
                syncTunnelState(now)
            }
            Sensor.TYPE_ROTATION_VECTOR -> {
                val rotationMatrix = FloatArray(9)
                SensorManager.getRotationMatrixFromVector(rotationMatrix, event.values)
                // Project device forward axis [0, 1, 0] in portrait orientation onto world ground plane (ENU):
                // v_world = R * [0, 1, 0]^T = [R[1], R[4], R[7]]
                // East = R[1], North = R[4]
                val eastComponent = rotationMatrix[1]
                val northComponent = rotationMatrix[4]
                val azimuthRad = kotlin.math.atan2(eastComponent, northComponent)
                estimator.onOrientation(azimuthRad, 0f, 0f)
            }
        }
    }

    /**
     * Push the machine's state into the estimator when it changes, and log the transition with
     * its trigger so a demo can be audited from logcat (D-080; the sidecar of rule R5 comes with
     * the trip-session milestone).
     */
    private fun syncTunnelState(nowMs: Long) {
        val state = fsm.state
        if (state == syncedTunnelState) return
        val t = fsm.lastTransition
        Log.i(
            TAG,
            "tunnel $syncedTunnelState -> $state via ${t?.trigger} at $nowMs ms " +
                "(cn0 ${fsm.cn0Top4DbHz}, used ${fsm.satellitesUsed}, lux ${fsm.lux}, forced ${fsm.forced})"
        )
        syncedTunnelState = state
        estimator.setTunnelState(state, nowMs)
    }

    private fun applyEstimate(estimate: Estimate, force: Boolean = false) {
        val nowMs = SystemClock.elapsedRealtime()
        if (!force && nowMs - lastUiPublishMs < 33L) {
            return
        }
        lastUiPublishMs = nowMs
        val fix = tunnelGeometry.locate(estimate.latitude, estimate.longitude)
        fsm.onPortalDistance(nowMs, portalDistanceM(fix))
        fsm.onMapInTunnel(nowMs, fix?.inside)
        // The 30 Hz publish tick doubles as the machine's clock for its timeouts.
        fsm.tick(nowMs)
        syncTunnelState(nowMs)

        // Route tracking: update along-track progress, maneuver countdown, ETA, and arrival
        val currentRoute = TelemetryStore.state.value.activeRoute
        val routeProgress = if (currentRoute != null) {
            RouteTracker.trackProgress(
                route = currentRoute,
                currentLat = estimate.latitude,
                currentLon = estimate.longitude,
                speedMps = estimate.speedMps,
                currentStepIndex = TelemetryStore.state.value.activeStepIndex
            )
        } else null

        TelemetryStore.update {
            it.copy(
                mode = estimate.mode,
                speedMps = estimate.speedMps,
                yawRad = estimate.yawRad,
                positionNorthM = estimate.positionNorthM,
                positionEastM = estimate.positionEastM,
                uncertaintyM = estimate.uncertaintyM,
                covNorthM2 = estimate.covNorthM2,
                covNorthEastM2 = estimate.covNorthEastM2,
                covEastM2 = estimate.covEastM2,
                poseElapsedMs = estimate.poseElapsedMs,
                gnssAvailable = estimate.gnssAvailable,
                tunnelModeActive = estimate.tunnelModeActive,
                tunnelState = fsm.state,
                tunnelTrigger = fsm.lastTransition?.trigger,
                tunnelForced = fsm.forced,
                tunnelOverride = fsm.overrideMode,
                tunnelFix = fix,
                cn0Top4DbHz = fsm.cn0Top4DbHz,
                ambientLux = fsm.lux,
                lastFixVerdict = estimate.lastFixVerdict,
                lastFixChi2 = estimate.lastFixChi2,
                outageAcceptedFixes = estimate.outageAcceptedFixes,
                outageRejectedFixes = estimate.outageRejectedFixes,
                lastExit = estimate.lastExit,
                stepCount = estimate.stepCount,
                latitude = estimate.latitude,
                longitude = estimate.longitude,
                originLat = estimate.originLat,
                originLon = estimate.originLon,
                path = estimate.path,
                totalDistanceM = estimate.totalDistanceM,
                tripDurationSec = estimate.tripDurationSec,
                sampleRateHz = currentRate,
                timestampJitterMs = currentJitter,
                lastSensorAgeMs = 0,
                satellites = satelliteCount,
                activeStepIndex = routeProgress?.stepIndex ?: it.activeStepIndex,
                remainingDistanceM = routeProgress?.remainingDistanceM ?: it.remainingDistanceM,
                remainingDurationSec = routeProgress?.remainingDurationSec ?: it.remainingDurationSec,
                distanceToNextStepM = routeProgress?.distanceToNextStepM ?: it.distanceToNextStepM,
                hasArrivedAtDestination = routeProgress?.hasArrived ?: it.hasArrivedAtDestination,
                isOffRoute = routeProgress?.isOffRoute ?: it.isOffRoute,
                routeProgressFraction = routeProgress?.progressFraction ?: it.routeProgressFraction
            )
        }
    }

    private var lastGpsFixElapsedMs = 0L

    override fun onLocationChanged(location: Location) {
        val now = SystemClock.elapsedRealtime()
        val isGpsOrFused = location.provider == LocationManager.GPS_PROVIDER || location.provider == "fused"
        if (isGpsOrFused) {
            lastGpsFixElapsedMs = now
        } else if (location.provider == LocationManager.NETWORK_PROVIDER) {
            // If GPS/fused fix was received recently, suppress coarse network fixes to eliminate jumping & drift
            if (now - lastGpsFixElapsedMs < 3_000L) {
                return
            }
            // A cell-tower or Wi-Fi position is not a satellite fix. While the tunnel machine
            // suppresses GNSS it must not see one as "satellites reappeared" (D-126), so network
            // fixes are dropped entirely in those states rather than gated and counted.
            if (fsm.state.suppressesGnss) {
                return
            }
        }

        // Heartbeat retention: inform estimator that GNSS updates are flowing
        estimator.notifyGnssHeartbeat()

        // Suppress coarse cell tower fixes (>100m error) once we already have an established origin
        if (location.hasAccuracy() && location.accuracy > 100f && estimator.hasOrigin()) {
            return
        }

        // The estimator gates the fix and reports its verdict; the machine decides what the
        // verdict means for the state; the estimator is told the new state before the next fix.
        val estimate = estimator.onLocation(location)
        fsm.onGnssFix(now, estimate.lastFixVerdict ?: FixVerdict.ACCEPTED)
        syncTunnelState(now)
        applyEstimate(estimator.snapshot(), force = true)
    }

    override fun onProviderDisabled(provider: String) {
        if (provider == LocationManager.GPS_PROVIDER) {
            TelemetryStore.update { it.copy(gnssAvailable = false, mode = NavigationMode.INS) }
        }
    }

    override fun onProviderEnabled(provider: String) = Unit
    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    override fun onDestroy() {
        activeInstance = null
        sensorManager.unregisterListener(this)
        locationManager.removeUpdates(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) locationManager.unregisterGnssStatusCallback(gnssCallback)
        // The machine and the estimator die with this instance; the state they published must
        // not outlive them, or the idle screen keeps a tunnel badge and a "GNSS suppressed" chip
        // over a recording that has ended. The pose, path and totals stay so the last drive
        // remains visible until the next Start.
        TelemetryStore.update {
            it.copy(
                running = false,
                mode = NavigationMode.INIT,
                tunnelModeActive = false,
                tunnelState = TunnelState.GNSS_HEALTHY,
                tunnelTrigger = null,
                tunnelForced = false,
                tunnelOverride = TunnelOverride.AUTO,
                tunnelFix = null,
                gnssAvailable = false,
                satellites = 0
            )
        }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun notification(): Notification = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("IDR Navigator active")
        .setContentText("Collecting uncalibrated IMU and GNSS timestamps")
        .setSmallIcon(android.R.drawable.ic_menu_compass)
        .setOngoing(true)
        .build()

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "Navigation recording", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    companion object {
        private const val TAG = "IDRTunnelFsm"
        const val CHANNEL_ID = "idr-recording"
        const val NOTIFICATION_ID = 26168
        const val REQUESTED_PERIOD_US = 5_000
        var startRequested = false
        private var activeInstance: SensorForegroundService? = null

        /**
         * Set the manual override mode for the tunnel state machine (D-126).
         */
        fun setTunnelOverride(mode: TunnelOverride): TunnelOverride {
            val service = activeInstance ?: return mode
            val now = SystemClock.elapsedRealtime()
            service.fsm.setOverride(now, mode)
            service.syncTunnelState(now)
            service.applyEstimate(service.estimator.snapshot(), force = true)
            return service.fsm.overrideMode
        }

        /**
         * The demo's manual override, kept next to the autonomous machine: forcing pins the
         * machine in tunnel mode; releasing it runs the honest exit path (verification, then
         * reconvergence) rather than snapping back to healthy.
         */
        fun toggleTunnelMode(): Boolean {
            val service = activeInstance ?: return false
            val next = if (service.fsm.forced) TunnelOverride.AUTO else TunnelOverride.FORCE_ON
            setTunnelOverride(next)
            return service.fsm.forced
        }

        fun resetOrigin() {
            val service = activeInstance ?: return
            val lm = service.locationManager
            val lastFused = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                try { lm.getLastKnownLocation(LocationManager.FUSED_PROVIDER) } catch (e: Exception) { null }
            } else null
            val lastGps = try { lm.getLastKnownLocation(LocationManager.GPS_PROVIDER) } catch (e: Exception) { null }
            val lastNet = try { lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER) } catch (e: Exception) { null }
            val freshLoc = lastFused ?: lastGps ?: lastNet
            service.estimator.resetOrigin(freshLoc)
            service.applyEstimate(service.estimator.snapshot(), force = true)
        }

        fun start(context: Context) {
            val intent = Intent(context, SensorForegroundService::class.java)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, SensorForegroundService::class.java))
        }
    }
}

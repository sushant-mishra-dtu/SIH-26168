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
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

class SensorForegroundService : Service(), SensorEventListener, LocationListener {
    private lateinit var sensorManager: SensorManager
    private lateinit var locationManager: LocationManager
    private var lastTimestampNs = 0L
    private var sampleCount = 0
    private var rateWindowStartNs = 0L
    private val estimator = LocalNavigationEstimator()
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
            TelemetryStore.update { it.copy(satellites = satelliteCount) }
        }
    }

    override fun onCreate() {
        super.onCreate()
        activeInstance = this
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, notification())
        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(LOCATION_SERVICE) as LocationManager

        val accel = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER_UNCALIBRATED)
            ?: sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        val gyro = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE_UNCALIBRATED)
            ?: sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        val rotVector = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)

        accel?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }
        gyro?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }
        rotVector?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }

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
                val estimate = estimator.onLocation(loc)
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

    private fun applyEstimate(estimate: Estimate, force: Boolean = false) {
        val nowMs = android.os.SystemClock.elapsedRealtime()
        if (!force && nowMs - lastUiPublishMs < 33L) {
            return
        }
        lastUiPublishMs = nowMs
        TelemetryStore.update {
            it.copy(
                mode = estimate.mode,
                speedMps = estimate.speedMps,
                yawRad = estimate.yawRad,
                positionNorthM = estimate.positionNorthM,
                positionEastM = estimate.positionEastM,
                uncertaintyM = estimate.uncertaintyM,
                gnssAvailable = estimate.gnssAvailable,
                tunnelModeActive = estimate.tunnelModeActive,
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
                satellites = satelliteCount
            )
        }
    }

    private var lastGpsFixElapsedMs = 0L

    override fun onLocationChanged(location: Location) {
        val now = android.os.SystemClock.elapsedRealtime()
        val isGpsOrFused = location.provider == LocationManager.GPS_PROVIDER || location.provider == "fused"
        if (isGpsOrFused) {
            lastGpsFixElapsedMs = now
        } else if (location.provider == LocationManager.NETWORK_PROVIDER) {
            // If GPS/fused fix was received recently, suppress coarse network fixes to eliminate jumping & drift
            if (now - lastGpsFixElapsedMs < 3_000L) {
                return
            }
        }

        // Heartbeat retention: inform estimator that GNSS updates are flowing
        estimator.notifyGnssHeartbeat()

        // Suppress coarse cell tower fixes (>100m error) once we already have an established origin
        if (location.hasAccuracy() && location.accuracy > 100f && estimator.hasOrigin()) {
            return
        }

        val estimate = estimator.onLocation(location)
        applyEstimate(estimate, force = true)
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
        TelemetryStore.update { it.copy(running = false) }
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
        const val CHANNEL_ID = "idr-recording"
        const val NOTIFICATION_ID = 26168
        const val REQUESTED_PERIOD_US = 5_000
        var startRequested = false
        private var activeInstance: SensorForegroundService? = null

        fun toggleTunnelMode(): Boolean {
            val service = activeInstance ?: return false
            val active = service.estimator.toggleTunnelMode()
            service.applyEstimate(service.estimator.snapshot(), force = true)
            return active
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

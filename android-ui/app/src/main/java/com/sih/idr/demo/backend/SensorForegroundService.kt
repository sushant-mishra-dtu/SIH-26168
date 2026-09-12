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
    private val gnssCallback = object : GnssStatus.Callback() {
        override fun onSatelliteStatusChanged(status: GnssStatus) {
            satelliteCount = (0 until status.satelliteCount).count { status.usedInFix(it) }
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, notification())
        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(LOCATION_SERVICE) as LocationManager
        val accel = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER_UNCALIBRATED)
        val gyro = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE_UNCALIBRATED)
        accel?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }
        gyro?.let { sensorManager.registerListener(this, it, REQUESTED_PERIOD_US) }
        TelemetryStore.update {
            it.copy(running = true, accelAvailable = accel != null, gyroAvailable = gyro != null)
        }
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0.5f, this)
            locationManager.registerGnssStatusCallback(gnssCallback, null)
        }
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type != Sensor.TYPE_GYROSCOPE_UNCALIBRATED) return
        val now = event.timestamp
        if (rateWindowStartNs == 0L) rateWindowStartNs = now
        sampleCount++
        val elapsedNs = now - rateWindowStartNs
        val rate = if (elapsedNs > 0) sampleCount * 1_000_000_000f / elapsedNs else 0f
        val jitter = if (lastTimestampNs == 0L) {
            0f
        } else {
            kotlin.math.abs((now - lastTimestampNs) / 1_000_000f - REQUESTED_PERIOD_US / 1000f)
        }
        lastTimestampNs = now
        val estimate = estimator.onGyro(event.values[2], now)
        TelemetryStore.update {
            it.copy(
                mode = estimate.mode,
                speedMps = estimate.speedMps,
                yawRad = estimate.yawRad,
                positionNorthM = estimate.positionNorthM,
                positionEastM = estimate.positionEastM,
                uncertaintyM = estimate.uncertaintyM,
                gnssAvailable = estimate.gnssAvailable,
                path = estimate.path,
                sampleRateHz = rate,
                timestampJitterMs = jitter,
                lastSensorAgeMs = 0
            )
        }
    }

    override fun onLocationChanged(location: Location) {
        val estimate = estimator.onLocation(location)
        TelemetryStore.update { state ->
            state.copy(
                mode = estimate.mode,
                gnssAvailable = estimate.gnssAvailable,
                satellites = satelliteCount,
                speedMps = estimate.speedMps,
                yawRad = estimate.yawRad,
                positionNorthM = estimate.positionNorthM,
                positionEastM = estimate.positionEastM,
                uncertaintyM = estimate.uncertaintyM,
                path = estimate.path
            )
        }
    }

    override fun onProviderDisabled(provider: String) {
        TelemetryStore.update { it.copy(gnssAvailable = false, mode = NavigationMode.INS) }
    }

    override fun onProviderEnabled(provider: String) = Unit
    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    override fun onDestroy() {
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

        fun start(context: Context) {
            val intent = Intent(context, SensorForegroundService::class.java)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, SensorForegroundService::class.java))
        }
    }
}

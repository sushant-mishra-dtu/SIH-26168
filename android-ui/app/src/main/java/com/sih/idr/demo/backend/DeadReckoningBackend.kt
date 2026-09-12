package com.sih.idr.demo.backend

import kotlinx.coroutines.flow.StateFlow

interface DeadReckoningBackend {
    val telemetry: StateFlow<TelemetryState>
    fun start()
    fun stop()
}

/** Current Android adapter. It owns collection; the native filter can be inserted behind this API. */
class AndroidSensorBackend : DeadReckoningBackend {
    override val telemetry: StateFlow<TelemetryState> = TelemetryStore.state

    override fun start() { SensorForegroundService.startRequested = true }
    override fun stop() { SensorForegroundService.startRequested = false }
}

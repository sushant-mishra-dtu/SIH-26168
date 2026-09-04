package org.idr26168.logger

import java.util.concurrent.atomic.AtomicReference

/**
 * The one channel from the service to the UI: a whole immutable snapshot, swapped atomically.
 *
 * The UI never reads the recorder's live counters. It reads a picture of them taken at a moment
 * the recorder chose. That is the same rule the demo UI will need later for the filter state
 * (`android/README.md`: "UI on main, reading a state snapshot") and it costs nothing to establish
 * now, on a struct where getting it wrong would only garble a label.
 */
object LoggerState {

    private val ref = AtomicReference(Snapshot.IDLE)

    val current: Snapshot get() = ref.get()

    fun publish(snapshot: Snapshot) {
        ref.set(snapshot)
    }

    fun reset() {
        ref.set(Snapshot.IDLE)
    }

    data class Snapshot(
        val running: Boolean,
        val sessionId: String?,
        val sessionDir: String?,
        val elapsedS: Double,
        val csvRows: Long,
        val csvDropped: Long,
        val rawRows: Long,
        val rawDropped: Long,
        val bytesOnDisk: Long,
        val streams: List<StreamReadout>,
        val gnss: GnssReadout?,
        val timebase: String,
        val warnings: List<String>,
    ) {
        companion object {
            val IDLE = Snapshot(
                running = false,
                sessionId = null,
                sessionDir = null,
                elapsedS = 0.0,
                csvRows = 0,
                csvDropped = 0,
                rawRows = 0,
                rawDropped = 0,
                bytesOnDisk = 0,
                streams = emptyList(),
                gnss = null,
                timebase = "unknown",
                warnings = emptyList(),
            )
        }
    }

    data class StreamReadout(
        val label: String,
        val requestedHz: Double,
        val achievedHz: Double,
        val dtMedianMs: Double,
        val dtP95Ms: Double,
        val dtStdevMs: Double,
        val events: Long,
        val nonMonotonic: Long,
        val batchArrivals: Long,
    )

    data class GnssReadout(
        val fixes: Long,
        val ageS: Double,
        val accuracyM: Double,
        val satsInView: Int,
        val usedInFix: Int,
        val meanCn0DbHz: Float,
    )
}

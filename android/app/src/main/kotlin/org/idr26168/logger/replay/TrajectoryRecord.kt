package org.idr26168.logger.replay

/**
 * Strongly typed representation of an `idr-trajectory/1` record.
 *
 * Emitted by `eval/run.py::trajectory_record` (TRAJECTORY_SCHEMA = "idr-trajectory/1").
 *
 * CRITICAL ARCHITECTURAL CONSTRAINTS (D-079, D-080, D-081):
 * - The Android view contains NO physics and NO simulation.
 * - Every displayed number (including per-epoch drift-% and yaw error) is computed by the producer
 *   of the record, never by the renderer.
 * - A record with an unrecognised schema string must be refused.
 * - The stream must disclaim 200 Hz FOG configuration if on the phone stream.
 */
data class TrajectoryRecord(
    val schema: String,
    val stamp: String,
    val reproducible: Boolean,
    val sequence: String,
    val stream: String,
    val imuRateHz: Int,
    val lengthS: Int,
    val startIdx: Int,
    val distanceM: Double,
    val epochS: List<Int>,
    val truthNed: List<NedPoint>,
    val filterNed: List<NedPoint>,
    val strapdownNed: List<NedPoint>,
    val gnssNed: List<NedPoint>?,
    val positionSigmaM: List<SigmaPoint>,
    val driftPct: List<Double>,
    val yawErrorDeg: List<Double>,
    val accelMps2: List<Vector3>,
    val gyroRps: List<Vector3>,
) {
    init {
        require(schema == SCHEMA) {
            "not an idr-trajectory/1 record. This view refuses a layout it does not recognise rather than drawing its fields in the wrong places."
        }
    }

    companion object {
        const val SCHEMA = "idr-trajectory/1"
    }
}

data class NedPoint(
    val north: Double,
    val east: Double,
    val down: Double = 0.0,
)

data class SigmaPoint(
    val sigmaNorth: Double,
    val sigmaEast: Double,
)

data class Vector3(
    val x: Double,
    val y: Double,
    val z: Double,
)

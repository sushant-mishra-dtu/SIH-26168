package org.idr26168.logger.replay

import org.json.JSONArray
import org.json.JSONObject

/**
 * Data model for `idr-trajectory/1` records emitted by `eval/run.py::trajectory_record`.
 *
 * **CRITICAL PROTOCOL REQUIREMENT (D-079, D-080):**
 * This class and its renderer contain NO physics and NO simulation. Every displayed metric
 * (including `driftPct` and `yawErrorDeg`) is read verbatim from the artefact produced by the
 * offline evaluation pipeline. No metric is derived or recomputed in the UI.
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
    val truthNed: List<DoubleArray>,
    val filterNed: List<DoubleArray>,
    val strapdownNed: List<DoubleArray>,
    val gnssNed: List<DoubleArray>?,
    val positionSigmaM: List<DoubleArray>,
    val driftPct: List<Double>,
    val yawErrorDeg: List<Double>,
    val accelMps2: List<DoubleArray>,
    val gyroRps: List<DoubleArray>,
) {
    companion object {
        const val REQUIRED_SCHEMA = "idr-trajectory/1"

        /**
         * Parses an `idr-trajectory/1` JSON string.
         * Refuses any record with an unrecognised schema.
         */
        fun fromJson(jsonString: String): TrajectoryRecord {
            val root = JSONObject(jsonString)
            val schema = root.optString("schema", "")
            if (schema != REQUIRED_SCHEMA) {
                throw IllegalArgumentException(
                    "Unrecognised schema: '$schema'. Expected '$REQUIRED_SCHEMA'. " +
                        "This renderer refuses a layout it does not recognise rather than " +
                        "drawing its fields in the wrong places."
                )
            }

            fun parse2D(array: JSONArray?): List<DoubleArray> {
                if (array == null) return emptyList()
                val list = ArrayList<DoubleArray>(array.length())
                for (i in 0 until array.length()) {
                    val sub = array.getJSONArray(i)
                    list.add(doubleArrayOf(sub.getDouble(0), sub.getDouble(1)))
                }
                return list
            }

            fun parse3D(array: JSONArray?): List<DoubleArray> {
                if (array == null) return emptyList()
                val list = ArrayList<DoubleArray>(array.length())
                for (i in 0 until array.length()) {
                    val sub = array.getJSONArray(i)
                    list.add(doubleArrayOf(sub.getDouble(0), sub.getDouble(1), sub.getDouble(2)))
                }
                return list
            }

            fun parseDoubleList(array: JSONArray?): List<Double> {
                if (array == null) return emptyList()
                val list = ArrayList<Double>(array.length())
                for (i in 0 until array.length()) {
                    list.add(array.getDouble(i))
                }
                return list
            }

            fun parseIntList(array: JSONArray?): List<Int> {
                if (array == null) return emptyList()
                val list = ArrayList<Int>(array.length())
                for (i in 0 until array.length()) {
                    list.add(array.getInt(i))
                }
                return list
            }

            val gnssArray = if (root.isNull("gnss_ned")) null else root.optJSONArray("gnss_ned")

            return TrajectoryRecord(
                schema = schema,
                stamp = root.optString("stamp", ""),
                reproducible = root.optBoolean("reproducible", true),
                sequence = root.optString("sequence", ""),
                stream = root.optString("stream", "S-"),
                imuRateHz = root.optInt("imu_rate_hz", 10),
                lengthS = root.optInt("length_s", 0),
                startIdx = root.optInt("start_idx", 0),
                distanceM = root.optDouble("distance_m", 0.0),
                epochS = parseIntList(root.optJSONArray("epoch_s")),
                truthNed = parse2D(root.optJSONArray("truth_ned")),
                filterNed = parse2D(root.optJSONArray("filter_ned")),
                strapdownNed = parse2D(root.optJSONArray("strapdown_ned")),
                gnssNed = if (gnssArray != null) parse2D(gnssArray) else null,
                positionSigmaM = parse2D(root.optJSONArray("position_sigma_m")),
                driftPct = parseDoubleList(root.optJSONArray("drift_pct")),
                yawErrorDeg = parseDoubleList(root.optJSONArray("yaw_error_deg")),
                accelMps2 = parse3D(root.optJSONArray("accel_mps2")),
                gyroRps = parse3D(root.optJSONArray("gyro_rps")),
            )
        }
    }
}

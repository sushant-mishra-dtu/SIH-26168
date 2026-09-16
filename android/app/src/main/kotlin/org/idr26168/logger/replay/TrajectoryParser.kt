package org.idr26168.logger.replay

/**
 * Robust, zero-dependency parser for `idr-trajectory/1` JSON records.
 *
 * Implemented with an internal recursive-descent parser so that it runs identically on
 * Android devices and in offline JVM unit tests without relying on stubbed framework classes.
 *
 * Rejection rule (D-079): A record with an unrecognised schema string is refused with
 * a visible message.
 */
object TrajectoryParser {

    fun parse(jsonString: String, label: String = "trajectory"): TrajectoryRecord {
        val root = try {
            JsonReader(jsonString).parseObject()
        } catch (e: Exception) {
            throw IllegalArgumentException("$label: invalid JSON (${e.message})", e)
        }

        val schema = root["schema"] as? String ?: ""
        if (schema != TrajectoryRecord.SCHEMA) {
            throw IllegalArgumentException(
                "$label: not an idr-trajectory/1 record. " +
                "This view refuses a layout it does not recognise rather than drawing its fields in the wrong places."
            )
        }

        val stamp = root["stamp"] as? String
            ?: throw IllegalArgumentException("$label: missing 'stamp'")
        val reproducible = root["reproducible"] as? Boolean ?: true
        val sequence = root["sequence"] as? String
            ?: throw IllegalArgumentException("$label: missing 'sequence'")
        val stream = root["stream"] as? String ?: "S-"
        val imuRateHz = (root["imu_rate_hz"] as? Number)?.toInt() ?: 10
        val lengthS = (root["length_s"] as? Number)?.toInt()
            ?: throw IllegalArgumentException("$label: missing 'length_s'")
        val startIdx = (root["start_idx"] as? Number)?.toInt() ?: 0
        val distanceM = (root["distance_m"] as? Number)?.toDouble()
            ?: throw IllegalArgumentException("$label: missing 'distance_m'")

        val epochS = parseListInt(root["epoch_s"])
        val truthNed = parseNedList(root["truth_ned"])
        val filterNed = parseNedList(root["filter_ned"])
        val strapdownNed = parseNedList(root["strapdown_ned"])
        val gnssNed = if (root["gnss_ned"] == null) null else parseNedList(root["gnss_ned"])
        val positionSigmaM = parseSigmaList(root["position_sigma_m"])
        val driftPct = parseListDouble(root["drift_pct"])
        val yawErrorDeg = parseListDouble(root["yaw_error_deg"])
        val accelMps2 = parseVector3List(root["accel_mps2"])
        val gyroRps = parseVector3List(root["gyro_rps"])

        return TrajectoryRecord(
            schema = schema,
            stamp = stamp,
            reproducible = reproducible,
            sequence = sequence,
            stream = stream,
            imuRateHz = imuRateHz,
            lengthS = lengthS,
            startIdx = startIdx,
            distanceM = distanceM,
            epochS = epochS,
            truthNed = truthNed,
            filterNed = filterNed,
            strapdownNed = strapdownNed,
            gnssNed = gnssNed,
            positionSigmaM = positionSigmaM,
            driftPct = driftPct,
            yawErrorDeg = yawErrorDeg,
            accelMps2 = accelMps2,
            gyroRps = gyroRps,
        )
    }

    @Suppress("UNCHECKED_CAST")
    private fun parseListInt(raw: Any?): List<Int> {
        val list = raw as? List<Any?> ?: return emptyList()
        return list.map { (it as Number).toInt() }
    }

    @Suppress("UNCHECKED_CAST")
    private fun parseListDouble(raw: Any?): List<Double> {
        val list = raw as? List<Any?> ?: return emptyList()
        return list.map { (it as Number).toDouble() }
    }

    @Suppress("UNCHECKED_CAST")
    private fun parseNedList(raw: Any?): List<NedPoint> {
        val list = raw as? List<Any?> ?: return emptyList()
        return list.map { item ->
            val coords = item as List<Any?>
            val north = (coords[0] as Number).toDouble()
            val east = (coords[1] as Number).toDouble()
            val down = if (coords.size > 2) (coords[2] as Number).toDouble() else 0.0
            NedPoint(north, east, down)
        }
    }

    @Suppress("UNCHECKED_CAST")
    private fun parseSigmaList(raw: Any?): List<SigmaPoint> {
        val list = raw as? List<Any?> ?: return emptyList()
        return list.map { item ->
            val sigmas = item as List<Any?>
            val sn = (sigmas[0] as Number).toDouble()
            val se = if (sigmas.size > 1) (sigmas[1] as Number).toDouble() else sn
            SigmaPoint(sn, se)
        }
    }

    @Suppress("UNCHECKED_CAST")
    private fun parseVector3List(raw: Any?): List<Vector3> {
        val list = raw as? List<Any?> ?: return emptyList()
        return list.map { item ->
            val v = item as List<Any?>
            val x = (v[0] as Number).toDouble()
            val y = (v[1] as Number).toDouble()
            val z = if (v.size > 2) (v[2] as Number).toDouble() else 0.0
            Vector3(x, y, z)
        }
    }

    /**
     * Minimal JSON tokenizer/parser without external framework dependencies.
     */
    private class JsonReader(private val src: String) {
        private var idx = 0
        private val len = src.length

        private fun skipWhitespace() {
            while (idx < len && src[idx].isWhitespace()) idx++
        }

        fun parseValue(): Any? {
            skipWhitespace()
            if (idx >= len) throw IllegalArgumentException("Unexpected end of JSON")
            return when (val c = src[idx]) {
                '{' -> parseObject()
                '[' -> parseArray()
                '"' -> parseString()
                't', 'f' -> parseBoolean()
                'n' -> parseNull()
                '-', in '0'..'9' -> parseNumber()
                else -> throw IllegalArgumentException("Unexpected character '$c' at offset $idx")
            }
        }

        fun parseObject(): Map<String, Any?> {
            requireChar('{')
            val map = LinkedHashMap<String, Any?>()
            skipWhitespace()
            if (idx < len && src[idx] == '}') {
                idx++
                return map
            }
            while (idx < len) {
                val key = parseString()
                requireChar(':')
                val value = parseValue()
                map[key] = value
                skipWhitespace()
                if (idx < len && src[idx] == ',') {
                    idx++
                    skipWhitespace()
                } else if (idx < len && src[idx] == '}') {
                    idx++
                    break
                } else {
                    throw IllegalArgumentException("Expected ',' or '}' in object at offset $idx")
                }
            }
            return map
        }

        private fun parseArray(): List<Any?> {
            requireChar('[')
            val list = ArrayList<Any?>()
            skipWhitespace()
            if (idx < len && src[idx] == ']') {
                idx++
                return list
            }
            while (idx < len) {
                list.add(parseValue())
                skipWhitespace()
                if (idx < len && src[idx] == ',') {
                    idx++
                    skipWhitespace()
                } else if (idx < len && src[idx] == ']') {
                    idx++
                    break
                } else {
                    throw IllegalArgumentException("Expected ',' or ']' in array at offset $idx")
                }
            }
            return list
        }

        private fun parseString(): String {
            requireChar('"')
            val sb = java.lang.StringBuilder()
            while (idx < len) {
                val c = src[idx++]
                if (c == '"') return sb.toString()
                if (c == '\\') {
                    if (idx >= len) throw IllegalArgumentException("Unterminated escape at $idx")
                    when (val esc = src[idx++]) {
                        '"' -> sb.append('"')
                        '\\' -> sb.append('\\')
                        '/' -> sb.append('/')
                        'b' -> sb.append('\b')
                        'f' -> sb.append('\u000C')
                        'n' -> sb.append('\n')
                        'r' -> sb.append('\r')
                        't' -> sb.append('\t')
                        'u' -> {
                            if (idx + 4 > len) throw IllegalArgumentException("Invalid unicode escape at $idx")
                            val hex = src.substring(idx, idx + 4)
                            idx += 4
                            sb.append(hex.toInt(16).toChar())
                        }
                        else -> sb.append(esc)
                    }
                } else {
                    sb.append(c)
                }
            }
            throw IllegalArgumentException("Unterminated string starting before offset $idx")
        }

        private fun parseNumber(): Number {
            skipWhitespace()
            val start = idx
            if (idx < len && src[idx] == '-') idx++
            while (idx < len && src[idx] in '0'..'9') idx++
            var isDouble = false
            if (idx < len && src[idx] == '.') {
                isDouble = true
                idx++
                while (idx < len && src[idx] in '0'..'9') idx++
            }
            if (idx < len && (src[idx] == 'e' || src[idx] == 'E')) {
                isDouble = true
                idx++
                if (idx < len && (src[idx] == '+' || src[idx] == '-')) idx++
                while (idx < len && src[idx] in '0'..'9') idx++
            }
            val numStr = src.substring(start, idx)
            return if (isDouble) numStr.toDouble() else (numStr.toLongOrNull() ?: numStr.toDouble())
        }

        private fun parseBoolean(): Boolean {
            skipWhitespace()
            return if (src.startsWith("true", idx)) {
                idx += 4
                true
            } else if (src.startsWith("false", idx)) {
                idx += 5
                false
            } else {
                throw IllegalArgumentException("Invalid boolean at offset $idx")
            }
        }

        private fun parseNull(): Any? {
            skipWhitespace()
            if (src.startsWith("null", idx)) {
                idx += 4
                return null
            }
            throw IllegalArgumentException("Invalid null token at offset $idx")
        }

        private fun requireChar(expected: Char) {
            skipWhitespace()
            if (idx >= len || src[idx] != expected) {
                val found = if (idx < len) src[idx] else "EOF"
                throw IllegalArgumentException("Expected '$expected' but found '$found' at offset $idx")
            }
            idx++
        }
    }
}

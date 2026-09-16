package org.idr26168.logger.replay

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/**
 * Unit tests for [TrajectoryParser] and [TrajectoryRecord].
 *
 * Verifies that the JSON record produced by `eval/run.py::trajectory_record` is parsed
 * accurately, and that records with an unknown schema or malformed content are refused.
 */
class TrajectoryParserTest {

    private fun sampleJson(
        schema: String = TrajectoryRecord.SCHEMA,
        reproducible: Boolean = true,
        sequence: String = "S3a",
        stream: String = "S-",
        imuRateHz: Int = 10,
        lengthS: Int = 2,
        distanceM: Double = 30.5,
        gnssNedNull: Boolean = false,
    ): String {
        val gnssStr = if (gnssNedNull) "null" else "[[0.0, 0.0, 0.0], [10.0, 1.0, 0.0], [20.0, 2.0, 0.0]]"
        return """
        {
            "schema": "$schema",
            "stamp": "2026-09-06T12:00:00Z git:abc1234 seed:0",
            "reproducible": $reproducible,
            "sequence": "$sequence",
            "stream": "$stream",
            "imu_rate_hz": $imuRateHz,
            "length_s": $lengthS,
            "start_idx": 100,
            "distance_m": $distanceM,
            "epoch_s": [0, 1, 2],
            "truth_ned": [[0.0, 0.0, 0.0], [10.0, 0.5, 0.0], [20.0, 1.0, 0.0]],
            "filter_ned": [[0.0, 0.0, 0.0], [9.8, 0.6, 0.0], [19.5, 1.2, 0.0]],
            "strapdown_ned": [[0.0, 0.0, 0.0], [15.0, 3.0, 0.0], [45.0, 12.0, 0.0]],
            "gnss_ned": $gnssStr,
            "position_sigma_m": [[0.5, 0.5], [1.2, 1.0], [2.4, 1.8]],
            "drift_pct": [0.0, 1.5, 3.2],
            "yaw_error_deg": [0.0, -0.4, 0.8],
            "accel_mps2": [
                [0.1, 0.0, 9.8], [0.2, 0.0, 9.8], [0.1, 0.0, 9.8], [0.1, 0.0, 9.8],
                [0.1, 0.0, 9.8], [0.2, 0.0, 9.8], [0.1, 0.0, 9.8], [0.1, 0.0, 9.8],
                [0.1, 0.0, 9.8], [0.2, 0.0, 9.8], [0.1, 0.0, 9.8], [0.1, 0.0, 9.8],
                [0.1, 0.0, 9.8], [0.2, 0.0, 9.8], [0.1, 0.0, 9.8], [0.1, 0.0, 9.8],
                [0.1, 0.0, 9.8], [0.2, 0.0, 9.8], [0.1, 0.0, 9.8], [0.1, 0.0, 9.8]
            ],
            "gyro_rps": [
                [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01],
                [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01],
                [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01],
                [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01],
                [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01], [0.0, 0.0, 0.01]
            ]
        }
        """.trimIndent()
    }

    @Test
    fun `parses a valid idr-trajectory-1 record completely`() {
        val json = sampleJson()
        val r = TrajectoryParser.parse(json, "test_S3a.json")

        assertEquals(TrajectoryRecord.SCHEMA, r.schema)
        assertEquals("S3a", r.sequence)
        assertEquals("S-", r.stream)
        assertEquals(10, r.imuRateHz)
        assertEquals(2, r.lengthS)
        assertEquals(30.5, r.distanceM, 1e-6)
        assertTrue(r.reproducible)
        assertEquals(3, r.epochS.size)
        assertEquals(3, r.truthNed.size)
        assertEquals(3, r.filterNed.size)
        assertEquals(3, r.strapdownNed.size)
        assertNotNull(r.gnssNed)
        assertEquals(3, r.gnssNed?.size)
        assertEquals(3, r.positionSigmaM.size)
        assertEquals(3, r.driftPct.size)
        assertEquals(3, r.yawErrorDeg.size)
        assertEquals(20, r.accelMps2.size)
        assertEquals(20, r.gyroRps.size)

        assertEquals(10.0, r.truthNed[1].north, 1e-6)
        assertEquals(0.5, r.truthNed[1].east, 1e-6)
        assertEquals(1.2, r.positionSigmaM[1].sigmaNorth, 1e-6)
        assertEquals(1.0, r.positionSigmaM[1].sigmaEast, 1e-6)
    }

    @Test
    fun `parses record with null gnss_ned when outage has no fix`() {
        val json = sampleJson(gnssNedNull = true)
        val r = TrajectoryParser.parse(json)
        assertNull(r.gnssNed)
    }

    @Test
    fun `marks dirty run when reproducible is false`() {
        val json = sampleJson(reproducible = false)
        val r = TrajectoryParser.parse(json)
        assertFalse(r.reproducible)
    }

    @Test
    fun `refuses unknown schema version with explicit message`() {
        val json = sampleJson(schema = "idr-trajectory/2")
        try {
            TrajectoryParser.parse(json, "bad_schema.json")
            fail("Expected IllegalArgumentException for unknown schema")
        } catch (e: IllegalArgumentException) {
            assertTrue(e.message?.contains("not an idr-trajectory/1 record") == true)
            assertTrue(e.message?.contains("This view refuses a layout it does not recognise") == true)
        }
    }

    @Test
    fun `refuses malformed JSON`() {
        try {
            TrajectoryParser.parse("{ not valid json }")
            fail("Expected IllegalArgumentException for malformed JSON")
        } catch (e: IllegalArgumentException) {
            assertTrue(e.message?.contains("invalid JSON") == true)
        }
    }
}

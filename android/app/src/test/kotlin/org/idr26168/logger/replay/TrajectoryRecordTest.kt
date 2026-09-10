package org.idr26168.logger.replay

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class TrajectoryRecordTest {

    private val sampleJson = """
    {
      "schema": "idr-trajectory/1",
      "stamp": "2026-09-03 14:00:00 [main:384a2ef]",
      "reproducible": true,
      "sequence": "S3a",
      "stream": "S-",
      "imu_rate_hz": 10,
      "length_s": 60,
      "start_idx": 100,
      "distance_m": 500.0,
      "epoch_s": [0, 1, 2],
      "truth_ned": [[0.0, 0.0], [10.0, 5.0], [20.0, 10.0]],
      "filter_ned": [[0.0, 0.0], [9.8, 5.1], [19.5, 10.2]],
      "strapdown_ned": [[0.0, 0.0], [9.5, 5.5], [18.0, 11.0]],
      "gnss_ned": [[0.0, 0.0], [10.1, 4.9], [20.0, 10.0]],
      "position_sigma_m": [[0.1, 0.1], [0.5, 0.4], [1.2, 0.9]],
      "drift_pct": [0.0, 0.15, 0.42],
      "yaw_error_deg": [0.0, -0.21, 0.85],
      "accel_mps2": [[0.0, 0.1, 9.81], [0.0, 0.2, 9.80]],
      "gyro_rps": [[0.0, 0.0, 0.01], [0.0, 0.0, 0.02]]
    }
    """.trimIndent()

    @Test
    fun testValidTrajectoryRecordParsing() {
        val record = TrajectoryRecord.fromJson(sampleJson)

        assertEquals("idr-trajectory/1", record.schema)
        assertEquals("S3a", record.sequence)
        assertEquals("S-", record.stream)
        assertEquals(10, record.imuRateHz)
        assertEquals(60, record.lengthS)
        assertEquals(500.0, record.distanceM, 1e-6)

        assertEquals(3, record.epochS.size)
        assertEquals(3, record.truthNed.size)
        assertEquals(3, record.filterNed.size)
        assertEquals(3, record.strapdownNed.size)
        assertNotNull(record.gnssNed)
        assertEquals(3, record.gnssNed!!.size)

        // Verify metrics are parsed verbatim without physics recomputation (D-079)
        assertEquals(0.0, record.driftPct[0], 1e-6)
        assertEquals(0.15, record.driftPct[1], 1e-6)
        assertEquals(0.42, record.driftPct[2], 1e-6)

        assertEquals(0.0, record.yawErrorDeg[0], 1e-6)
        assertEquals(-0.21, record.yawErrorDeg[1], 1e-6)
        assertEquals(0.85, record.yawErrorDeg[2], 1e-6)
    }

    @Test(expected = IllegalArgumentException::class)
    fun testRefusesUnrecognisedSchema() {
        val invalidJson = sampleJson.replace("idr-trajectory/1", "idr-trajectory/2")
        TrajectoryRecord.fromJson(invalidJson)
    }

    @Test
    fun testErrorMessageContainsExpectedSchemaDetails() {
        try {
            val invalidJson = sampleJson.replace("idr-trajectory/1", "legacy-schema")
            TrajectoryRecord.fromJson(invalidJson)
        } catch (e: IllegalArgumentException) {
            assertTrue(e.message!!.contains("Unrecognised schema"))
            assertTrue(e.message!!.contains("Expected 'idr-trajectory/1'"))
        }
    }

    @Test
    fun testNoPhysicsRecomputationOrRngInReplayPackage() {
        val replayDir = File("src/main/kotlin/org/idr26168/logger/replay")
        val files = replayDir.listFiles()?.filter { it.extension == "kt" } ?: emptyList()
        assertTrue("Replay Kotlin files must exist", files.isNotEmpty())

        for (file in files) {
            val text = file.readText()
            // D-079: Replay view must never recompute physics by dividing by distanceM
            assertFalse(
                "${file.name} contains division by distanceM (D-079 violation)",
                text.contains("/ distanceM") || text.contains("/ distance_m") || text.contains("/distanceM")
            )
            // D-080: Replay view must contain no random generator or simulated fallback
            assertFalse(
                "${file.name} contains random/generator (D-080 violation)",
                text.contains("Math.random") || text.contains("Random.") || text.contains("kotlin.random")
            )
        }
    }
}

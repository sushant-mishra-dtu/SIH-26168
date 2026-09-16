package org.idr26168.logger.replay

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Architectural invariant tests for the Android Replay View.
 *
 * Mirrors `tests/test_replay.py` for the Android codebase, mechanically enforcing:
 * - D-039 / D-080: No simulation, no RNG, no synthetic data generators, no network.
 * - D-079: The view computes no physics. Drift-% and yaw error are never re-derived or divided by distance_m.
 * - D-081: 200 Hz FOG disclaimer and S- 10 Hz stream identification in captions.
 */
class ReplayRuleTest {

    private val replayDir: File by lazy {
        // Find the replay source directory
        val candidates = listOf(
            File("src/main/kotlin/org/idr26168/logger/replay"),
            File("app/src/main/kotlin/org/idr26168/logger/replay"),
            File("android/app/src/main/kotlin/org/idr26168/logger/replay")
        )
        candidates.firstOrNull { it.exists() }
            ?: throw IllegalStateException("Cannot find replay source directory from ${File(".").absolutePath}")
    }

    private val allReplaySources: List<File> by lazy {
        replayDir.walk().filter { it.extension == "kt" }.toList()
    }

    @Test
    fun `the replay view computes no physics and never divides by distance`() {
        for (file in allReplaySources) {
            val text = file.readText()
            assertFalse(
                "File ${file.name} must not divide by distanceM (D-079)",
                text.contains("/ distanceM") || text.contains("/ r.distanceM")
            )
            assertFalse(
                "File ${file.name} must not compute atan2 (D-079: yaw error must come from record)",
                text.contains("atan2")
            )
        }
    }

    @Test
    fun `the replay view has no random numbers or synthetic generators`() {
        for (file in allReplaySources) {
            val text = file.readText()
            assertFalse(
                "File ${file.name} must not use Random (D-080)",
                text.contains("kotlin.random.Random") || text.contains("java.util.Random") || text.contains("Math.random")
            )
        }
    }

    @Test
    fun `the replay view makes no network requests`() {
        for (file in allReplaySources) {
            val text = file.readText()
            assertFalse(
                "File ${file.name} must not make HTTP requests (D-041, D-080: 100% offline)",
                text.contains("HttpURLConnection") || text.contains("okhttp") || text.contains("HttpClient")
            )
        }
    }

    @Test
    fun `the sensor caption identifies the S- 10 Hz stream and disclaims 200 Hz FOG`() {
        val replayActivity = File(replayDir, "ReplayActivity.kt").readText()
        assertTrue(
            "Replay caption must name smartphone stream and rate (D-081)",
            replayActivity.contains("smartphone stream at %d Hz") || replayActivity.contains("smartphone stream at 10 Hz")
        )
        assertTrue(
            "Replay caption must explicitly disclaim 200 Hz FOG (D-081)",
            replayActivity.contains("200 Hz FOG configuration is not demonstrated on this dataset")
        )
    }

    @Test
    fun `the schema guard is enforced against non idr-trajectory-1 records`() {
        val parserText = File(replayDir, "TrajectoryParser.kt").readText()
        assertTrue(
            "TrajectoryParser must reject unknown schema with exact message (D-079)",
            parserText.contains("not an idr-trajectory/1 record")
        )
    }
}

package org.idr26168.logger

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.zip.ZipInputStream

class SessionExporterTest {

    @get:Rule
    val tmp = TemporaryFolder()

    @Test
    fun testZipSessionPackagesCsvAndSidecarJsonTogether() {
        val sessionDir = tmp.newFolder("S-IDR-20260903-120000-pixel")
        val csvFile = File(sessionDir, "S-IDR-20260903-120000-pixel.csv")
        val jsonFile = File(sessionDir, "S-IDR-20260903-120000-pixel_session.json")
        val rawCsvFile = File(sessionDir, "S-IDR-20260903-120000-pixel_raw_imu.csv")

        csvFile.writeText("date,gps_speed_kmh,accel_x,accel_y,accel_z\n2026-09-03 12:00:00.000,0,0,0,9.81\n")
        jsonFile.writeText("{\"schema\":\"idr-logger-session/1\",\"session_id\":\"S-IDR-20260903-120000-pixel\"}")
        rawCsvFile.writeText("stamp_ns,accel_uncal_x,accel_uncal_y,accel_uncal_z\n1000000000,0,0,9.81\n")

        val out = ByteArrayOutputStream()
        val zippedNames = SessionExporter.zipSession(sessionDir, out)

        assertEquals(3, zippedNames.size)
        assertTrue(zippedNames.contains("S-IDR-20260903-120000-pixel.csv"))
        assertTrue(zippedNames.contains("S-IDR-20260903-120000-pixel_session.json"))
        assertTrue(zippedNames.contains("S-IDR-20260903-120000-pixel_raw_imu.csv"))

        // Unpack zip and verify contents
        val entries = mutableMapOf<String, String>()
        ZipInputStream(ByteArrayInputStream(out.toByteArray())).use { zipIn ->
            var entry = zipIn.nextEntry
            while (entry != null) {
                entries[entry.name] = zipIn.readBytes().toString(Charsets.UTF_8)
                zipIn.closeEntry()
                entry = zipIn.nextEntry
            }
        }

        assertTrue(entries.containsKey("S-IDR-20260903-120000-pixel.csv"))
        assertTrue(entries.containsKey("S-IDR-20260903-120000-pixel_session.json"))
        assertTrue(entries["S-IDR-20260903-120000-pixel_session.json"]!!.contains("idr-logger-session/1"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun testZipSessionThrowsForEmptyDirectory() {
        val emptyDir = tmp.newFolder("empty")
        val out = ByteArrayOutputStream()
        SessionExporter.zipSession(emptyDir, out)
    }
}

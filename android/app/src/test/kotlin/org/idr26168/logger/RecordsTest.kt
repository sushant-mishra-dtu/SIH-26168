package org.idr26168.logger

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The shape of the row that reaches the harness.
 *
 * `tests/test_android_logger_schema.py` already asserts the *header* against the live loader, and
 * it does that in Python because the loader is the authority on what is readable. What it cannot
 * see is the Kotlin that writes the row underneath that header: it hand-writes three example rows
 * and checks those load. So the header is pinned on one side of the wall and the row on the other,
 * and nothing until now checked that the two agree on how many fields there are.
 *
 * That gap is the expensive one. A row one field short of its header loads without complaint and
 * silently shifts every GNSS column left, which reads as a plausible trajectory in the wrong place.
 * The first assertion below is therefore the important one: the row width is compared against
 * [Channels.HEADER] itself, not against the number 24.
 */
class RecordsTest {

    private val date = "2026-09-03 14:05:07.100"

    private fun fields(row: Records.CsvRow): List<String> {
        val sb = StringBuilder()
        Records.formatCsvRow(row, sb)
        val text = sb.toString()
        assertFalse("a row must not contain a newline; the writer appends it", text.contains('\n'))
        return text.split(",")
    }

    private fun row(
        timeSinceStartMs: Double = 100.0,
        accel: FloatArray? = null,
        gravity: FloatArray? = null,
        gyro: FloatArray? = null,
        magnetic: FloatArray? = null,
        orientationDeg: FloatArray? = null,
        fix: GnssHub.Fix? = null,
        dateText: String = date,
    ) = Records.CsvRow(
        timeSinceStartMs, accel, gravity, gyro, magnetic, orientationDeg, fix, dateText,
    )

    private fun fix(
        latDeg: Double = 28.545,
        lonDeg: Double = 77.191,
        altitudeM: Double? = 216.4,
        speedMps: Double? = 12.4,
        accuracyM: Double? = 4.1,
        bearingDeg: Double? = 88.1,
        satsInView: Int = 17,
    ) = GnssHub.Fix(
        latDeg = latDeg,
        lonDeg = lonDeg,
        altitudeM = altitudeM,
        speedMps = speedMps,
        accuracyM = accuracyM,
        bearingDeg = bearingDeg,
        satsInView = satsInView,
        usedInFix = 12,
        meanCn0DbHz = 31.5f,
        topCn0DbHz = 44.0f,
        elapsedRealtimeNs = 5_000_000_000L,
    )

    // -- shape ------------------------------------------------------------------------------------

    @Test
    fun `a row has exactly as many fields as the header has columns`() {
        // Compared against the header itself. If someone adds a column to Channels.HEADER without
        // adding a field here, this fails before a drive is recorded rather than after one.
        assertEquals(Channels.HEADER.size, fields(row()).size)
        assertEquals(Channels.HEADER.size, fields(row(fix = fix())).size)
        assertEquals(
            Channels.HEADER.size,
            fields(
                row(
                    accel = floatArrayOf(0.012f, -0.043f, 9.802f),
                    gravity = floatArrayOf(0.001f, -0.002f, 9.806f),
                    gyro = floatArrayOf(0.0011f, -0.0004f, 0.0002f),
                    magnetic = floatArrayOf(12.30f, -4.10f, -38.20f),
                    orientationDeg = floatArrayOf(91.4f, 1.2f, -0.3f),
                    fix = fix(),
                )
            ).size,
        )
    }

    @Test
    fun `the width is 24 and the header agrees`() {
        // The Python suite asserts 24 from the other side of the wall. Stating it here too means
        // a change to one of the two files cannot quietly pass by only being made in that file.
        assertEquals(24, Channels.HEADER.size)
        assertEquals(24, fields(row()).size)
    }

    @Test
    fun `the date is the last field and is written through unchanged`() {
        val f = fields(row(fix = fix()))
        assertEquals(date, f.last())
        assertEquals("date", Channels.HEADER.last().lowercase().substringBefore(" "))
    }

    // -- empty cells, and why they are not zeros ------------------------------------------------

    @Test
    fun `before the first fix the seven GNSS cells are empty and not zero`() {
        // A zero latitude is a real place in the Gulf of Guinea and would load as one. The loader
        // takes fixes as position changes, so a fabricated 0,0 would enter the trajectory.
        val f = fields(row(fix = null))
        for (i in 16..22) {
            assertEquals("GNSS field $i should be an empty cell before the first fix", "", f[i])
        }
        assertEquals(date, f[23])
    }

    @Test
    fun `a channel with no sample yet writes empty cells rather than zeros`() {
        // Same argument for the inertial channels: a phone that has not yet delivered a gravity
        // event has not measured 0.0 m per s squared, and free fall is a thing the filter models.
        val f = fields(row(accel = floatArrayOf(1f, 2f, 3f)))
        assertEquals("1.000000", f[1])
        for (i in 4..15) {
            assertEquals("field $i should be empty when the channel has no sample", "", f[i])
        }
    }

    @Test
    fun `the optional parts of a fix are individually omitted`() {
        // Location.hasAltitude / hasSpeed / hasAccuracy / hasBearing are all independently false
        // on a fresh fix, and each missing one has to leave its own cell empty without disturbing
        // the fields either side of it.
        val f = fields(row(fix = fix(altitudeM = null, speedMps = null, accuracyM = null, bearingDeg = null)))
        assertEquals("28.54500000", f[16])
        assertEquals("77.19100000", f[17])
        assertEquals("", f[18])
        assertEquals("", f[19])
        assertEquals("", f[20])
        assertEquals("", f[21])
        assertEquals("17", f[22])
    }

    // -- precision --------------------------------------------------------------------------------

    @Test
    fun `inertial channels carry six decimal places`() {
        // Six is three orders below the quantisation step of a phone IMU, so rounding here can
        // never be mistaken for sensor noise in an Allan plot.
        val f = fields(
            row(
                accel = floatArrayOf(0.012f, -0.043f, 9.802f),
                gravity = floatArrayOf(0.001f, -0.002f, 9.806f),
                gyro = floatArrayOf(0.0011f, -0.0004f, 0.0002f),
                magnetic = floatArrayOf(12.30f, -4.10f, -38.20f),
            )
        )
        assertEquals(listOf("0.012000", "-0.043000", "9.802000"), f.subList(1, 4))
        assertEquals(listOf("0.001000", "-0.002000", "9.806000"), f.subList(4, 7))
        assertEquals(listOf("0.001100", "-0.000400", "0.000200"), f.subList(7, 10))
        // Note the last one: -38.200001, not -38.200000. Six decimal places is finer than a Float
        // can represent, so widening -38.20f to Double exposes the float's own representation
        // error (-38.200000762939453) and the sixth place shows it. That is the sensor's value
        // printed exactly, not a rounding bug -- the error is 1e-6 uT against a magnetometer that
        // resolves about 0.1 uT. It is asserted rather than smoothed over because the alternative
        // is someone finding it in a recording and going looking for a fault that is not there.
        assertEquals(listOf("12.300000", "-4.100000", "-38.200001"), f.subList(10, 13))
    }

    @Test
    fun `orientation carries three decimal places and latitude carries eight`() {
        val f = fields(row(orientationDeg = floatArrayOf(91.4f, 1.2f, -0.3f), fix = fix()))
        assertEquals(listOf("91.400", "1.200", "-0.300"), f.subList(13, 16))
        // 1e-8 deg is about 1.1 mm. GNSS accuracy is metres, but truncating below a millimetre
        // would put a quantisation floor under a trajectory that gets differentiated.
        assertEquals("28.54500000", f[16])
        assertEquals("77.19100000", f[17])
        assertEquals(listOf("216.400", "12.400", "4.100", "88.100"), f.subList(18, 22))
    }

    @Test
    fun `time since start carries one decimal place`() {
        assertEquals("0.0", fields(row(timeSinceStartMs = 0.0))[0])
        assertEquals("100.0", fields(row(timeSinceStartMs = 100.0))[0])
        assertEquals("1234.6", fields(row(timeSinceStartMs = 1234.56))[0])
    }

    @Test
    fun `numbers are formatted in the C locale whatever the device is set to`() {
        // A device in a comma-decimal locale would otherwise write "9,802" into a CSV, which does
        // not fail -- it shifts every later column by one and loads as a different row.
        val previous = java.util.Locale.getDefault()
        try {
            java.util.Locale.setDefault(java.util.Locale.GERMANY)
            val f = fields(row(accel = floatArrayOf(9.802f, 0f, 0f), fix = fix()))
            assertEquals(Channels.HEADER.size, f.size)
            assertEquals("9.802000", f[1])
            assertEquals("28.54500000", f[16])
        } finally {
            java.util.Locale.setDefault(previous)
        }
    }

    // -- the values that must never reach the file ---------------------------------------------

    @Test
    fun `NaN and infinity become empty cells and are never written as text`() {
        // "NaN" in a numeric column makes pandas read the whole column as object dtype, and the
        // failure then surfaces somewhere else entirely.
        val f = fields(
            row(
                accel = floatArrayOf(Float.NaN, Float.POSITIVE_INFINITY, 1.0f),
                gyro = floatArrayOf(Float.NEGATIVE_INFINITY, 2.0f, Float.NaN),
            )
        )
        assertEquals(Channels.HEADER.size, f.size)
        assertEquals(listOf("", "", "1.000000"), f.subList(1, 4))
        assertEquals(listOf("", "2.000000", ""), f.subList(7, 10))
    }

    @Test
    fun `no rendering of a row contains the word NaN or infinity in any casing`() {
        val sb = StringBuilder()
        Records.formatCsvRow(
            row(
                timeSinceStartMs = Double.NaN,
                accel = floatArrayOf(Float.NaN, Float.NaN, Float.NaN),
                gravity = floatArrayOf(Float.POSITIVE_INFINITY, 0f, 0f),
                fix = fix(latDeg = Double.NaN, altitudeM = Double.NaN),
            ),
            sb,
        )
        val text = sb.toString().lowercase()
        assertFalse(text, text.contains("nan"))
        assertFalse(text, text.contains("inf"))
        // Even with a NaN in the first field, the row keeps its width.
        assertEquals(Channels.HEADER.size, sb.toString().split(",").size)
    }

    @Test
    fun `a row never contains a stray comma that would shift the columns`() {
        val f = fields(row(fix = fix(), orientationDeg = floatArrayOf(91.4f, 1.2f, -0.3f)))
        // Every field is either empty or free of quoting problems: no field may itself need to be
        // quoted, because nothing in the writer quotes anything.
        for (cell in f) {
            assertFalse("cell $cell needs CSV quoting", cell.contains('"'))
            assertFalse("cell $cell needs CSV quoting", cell.contains('\r'))
        }
    }

    // -- the raw sidecar ---------------------------------------------------------------------------

    @Test
    fun `a raw sample has as many fields as the raw header has columns`() {
        val sb = StringBuilder()
        Records.formatRawSample(
            SensorHub.RawSample(
                key = "accelerometer_uncalibrated",
                eventNs = 123_456_789L,
                arrivalNs = 123_654_321L,
                accuracy = 3,
                values = floatArrayOf(0.1f, 0.2f, 0.3f, 0.01f, 0.02f, 0.03f),
            ),
            sb,
        )
        val f = sb.toString().split(",")
        assertEquals(Records.RAW_IMU_HEADER.split(",").size, f.size)
        assertEquals("accelerometer_uncalibrated", f[0])
        assertEquals("123456789", f[1])
        assertEquals("123654321", f[2])
        assertEquals("3", f[3])
        // v0..v2 uncorrected, v3..v5 the OS bias estimate that arrived with them. Keeping both is
        // what makes the pair reversible after the fact.
        assertEquals(listOf("0.100000", "0.200000", "0.300000"), f.subList(4, 7))
        assertEquals(listOf("0.010000", "0.020000", "0.030000"), f.subList(7, 10))
    }

    @Test
    fun `a raw sample with fewer than six values keeps the row rectangular`() {
        // A calibrated three-axis type reaching this path must not shorten the row; the file has
        // to stay loadable without a parser that counts fields per line.
        val sb = StringBuilder()
        Records.formatRawSample(
            SensorHub.RawSample("gyroscope_uncalibrated", 1L, 2L, 0, floatArrayOf(1f, 2f, 3f)),
            sb,
        )
        val f = sb.toString().split(",")
        assertEquals(Records.RAW_IMU_HEADER.split(",").size, f.size)
        assertEquals(listOf("1.000000", "2.000000", "3.000000"), f.subList(4, 7))
        assertEquals(listOf("", "", ""), f.subList(7, 10))
    }

    // -- the unit crossing -------------------------------------------------------------------------

    @Test
    fun `speed crosses the wall in metres per second and is not scaled`() {
        // D-109. Location.getSpeed() is m/s and gps_speed_mps is m/s, so the crossing is a
        // widening and nothing else. The `* 3.6` this test used to pin was right about the
        // `GPS SPEED (Kmh)` header and wrong about the bytes -- D-102 removed the matching
        // `/ 3.6` downstream, and a factor here would now survive all the way into a result.
        assertEquals(10.0, Channels.mps(10.0f), 1e-9)
        assertEquals(0.0, Channels.mps(0.0f), 0.0)
    }
}

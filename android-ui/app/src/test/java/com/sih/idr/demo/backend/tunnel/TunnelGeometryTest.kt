package com.sih.idr.demo.backend.tunnel

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.cos

/**
 * Unit tests for tunnel geometry projection, portal distance derivation, and corridor containment (D-126).
 */
class TunnelGeometryTest {

    private val origin = LatLon(28.6129, 77.2295)
    // 600 m straight north from origin
    private val exitStraight = LatLon(28.6129 + 600.0 / 111_320.0, 77.2295)
    private val straightTunnel = TunnelDef(
        id = "straight-600m",
        name = "Straight Test Tunnel",
        centreline = listOf(origin, exitStraight),
        lengthM = 600.0,
        postedLimitKmh = null
    )
    private val straightGeometry = TunnelGeometry(listOf(straightTunnel))

    @Test
    fun point100mBeforeEntryIsNotInsideAndHasCorrectDistanceToEntry() {
        // Point 100 m south of the entry portal
        val lat = origin.lat - 100.0 / 111_320.0
        val lon = origin.lon
        val fix = straightGeometry.locate(lat, lon)

        assertNotNull(fix)
        assertFalse(fix!!.inside)
        assertEquals(100.0, fix.distanceToEntryM, 2.0)
        assertEquals(100.0f, portalDistanceM(fix)!!, 2.0f)
    }

    @Test
    fun point250mAlongStraightTunnelIsInsideWithCorrectAlongAndRemaining() {
        // Point 250 m north of entry portal along the 600 m bore
        val lat = origin.lat + 250.0 / 111_320.0
        val lon = origin.lon
        val fix = straightGeometry.locate(lat, lon)

        assertNotNull(fix)
        assertTrue(fix!!.inside)
        assertEquals(250.0, fix.alongM, 2.0)
        assertEquals(350.0, fix.remainingM, 2.0)
        assertEquals(0.0, fix.distanceToEntryM, 0.001)
        assertEquals(350.0f, portalDistanceM(fix)!!, 2.0f)
    }

    @Test
    fun point50mLateralOfCentrelineIsNotInside() {
        // Point at 250 m along bore, but 50 m east of centreline (> 30 m default maxLateralM)
        val lat = origin.lat + 250.0 / 111_320.0
        val cosLat = cos(Math.toRadians(lat))
        val lon = origin.lon + 50.0 / (111_320.0 * cosLat)
        val fix = straightGeometry.locate(lat, lon)

        assertNotNull(fix)
        assertFalse(fix!!.inside)
        assertEquals(50.0, fix.lateralM, 2.0)
    }

    @Test
    fun pointPastExitIsNotInsideAndPortalDistanceIsNull() {
        // Point 50 m past the 600 m exit portal (650 m along)
        val lat = origin.lat + 650.0 / 111_320.0
        val lon = origin.lon
        val fix = straightGeometry.locate(lat, lon)

        assertNotNull(fix)
        assertFalse(fix!!.inside)
        assertTrue(fix.alongM > 600.0)
        assertNull(portalDistanceM(fix))
    }

    @Test
    fun twoSegmentBentCentrelineProjectsOntoCorrectSegment() {
        // A two-segment tunnel: 300 m North, then 300 m East (total 600 m)
        val p0 = LatLon(28.6129, 77.2295)
        val p1 = LatLon(28.6129 + 300.0 / 111_320.0, 77.2295)
        val cosLatP1 = cos(Math.toRadians(p1.lat))
        val p2 = LatLon(p1.lat, p1.lon + 300.0 / (111_320.0 * cosLatP1))
        val bentTunnel = TunnelDef("bent-600m", "Bent Test Tunnel", listOf(p0, p1, p2), 600.0, 50)
        val bentGeometry = TunnelGeometry(listOf(bentTunnel))

        // Query point near segment 0: 150 m North, 5 m East
        val latA = 28.6129 + 150.0 / 111_320.0
        val cosLatA = cos(Math.toRadians(latA))
        val lonA = 77.2295 + 5.0 / (111_320.0 * cosLatA)
        val fixA = bentGeometry.locate(latA, lonA)
        assertNotNull(fixA)
        assertTrue(fixA!!.inside)
        assertEquals(150.0, fixA.alongM, 2.0)
        assertEquals(5.0, fixA.lateralM, 2.0)
        assertEquals(450.0, fixA.remainingM, 2.0)

        // Query point near segment 1: 305 m North (5 m lateral of segment 1), 150 m East along segment 1
        val latB = p1.lat + 5.0 / 111_320.0
        val lonB = p1.lon + 150.0 / (111_320.0 * cosLatP1)
        val fixB = bentGeometry.locate(latB, lonB)
        assertNotNull(fixB)
        assertTrue(fixB!!.inside)
        assertEquals(450.0, fixB.alongM, 2.0)
        assertEquals(5.0, fixB.lateralM, 2.0)
        assertEquals(150.0, fixB.remainingM, 2.0)
    }

    @Test
    fun emptyGeometryReturnsNull() {
        val empty = TunnelGeometry(emptyList())
        assertNull(empty.locate(28.6129, 77.2295))
    }

    @Test
    fun nanCoordinatesReturnNull() {
        assertNull(straightGeometry.locate(Double.NaN, 77.2295))
        assertNull(straightGeometry.locate(28.6129, Double.NaN))
    }

    @Test
    fun centrelineLengthComputationSumsSegmentLengths() {
        val p0 = LatLon(28.6129, 77.2295)
        val p1 = LatLon(28.6129 + 200.0 / 111_320.0, 77.2295)
        val p2 = LatLon(28.6129 + 500.0 / 111_320.0, 77.2295)
        val len = computeCentrelineLengthM(listOf(p0, p1, p2))
        assertEquals(500.0, len, 1.0)
    }
}

package com.sih.idr.demo.backend.routing

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RouteTrackerTest {

    private val origin = GeoCoordinate(28.6129, 77.2295)
    private val waypoint1 = GeoCoordinate(28.6150, 77.2295)
    private val waypoint2 = GeoCoordinate(28.6180, 77.2295)
    private val destination = GeoCoordinate(28.6200, 77.2295)

    private val testRoute = NavigationRoute(
        destinationName = "Connaught Place",
        destinationCoord = destination,
        distanceMeters = 800f,
        durationSeconds = 120L,
        points = listOf(origin, waypoint1, waypoint2, destination),
        steps = listOf(
            RouteManeuver(
                instruction = "Head north toward Waypoint 1",
                distanceM = 230f,
                maneuverType = ManeuverType.STRAIGHT,
                coordinate = waypoint1,
                streetName = "Barakhamba Road"
            ),
            RouteManeuver(
                instruction = "Continue straight past Waypoint 2",
                distanceM = 330f,
                maneuverType = ManeuverType.STRAIGHT,
                coordinate = waypoint2,
                streetName = "Outer Circle"
            ),
            RouteManeuver(
                instruction = "Arrive at Connaught Place",
                distanceM = 220f,
                maneuverType = ManeuverType.ARRIVE,
                coordinate = destination,
                streetName = "Inner Circle"
            )
        )
    )

    @Test
    fun testInitialTrackingAtStart() {
        val progress = RouteTracker.trackProgress(
            route = testRoute,
            currentLat = origin.latitude,
            currentLon = origin.longitude,
            speedMps = 10f,
            currentStepIndex = 0
        )

        assertFalse("Should not be arrived at origin", progress.hasArrived)
        assertFalse("Should not be off route at origin", progress.isOffRoute)
        assertEquals("Should start at step 0", 0, progress.stepIndex)
        assertTrue("Remaining distance should be positive", progress.remainingDistanceM > 700f)
        assertTrue("Distance to next step should be positive", progress.distanceToNextStepM > 100f)
    }

    @Test
    fun testStepAdvanceWhenNearWaypoint() {
        // Vehicle is right at waypoint1 (within 10m)
        val progress = RouteTracker.trackProgress(
            route = testRoute,
            currentLat = waypoint1.latitude,
            currentLon = waypoint1.longitude,
            speedMps = 8f,
            currentStepIndex = 0
        )

        assertEquals("Should advance to step 1 when within 30m of waypoint 1", 1, progress.stepIndex)
        assertFalse("Should not be arrived yet", progress.hasArrived)
    }

    @Test
    fun testDestinationArrival() {
        // Vehicle is within 15m of destination
        val progress = RouteTracker.trackProgress(
            route = testRoute,
            currentLat = destination.latitude,
            currentLon = destination.longitude,
            speedMps = 0f,
            currentStepIndex = 2
        )

        assertTrue("Should detect arrival at destination", progress.hasArrived)
        assertEquals("Remaining distance should be 0 upon arrival", 0f, progress.remainingDistanceM, 0.01f)
        assertEquals("Progress fraction should be 1.0 upon arrival", 1.0f, progress.progressFraction, 0.01f)
    }

    @Test
    fun testOffRouteDetection() {
        // Vehicle is 200m to the east (deviated from north-south corridor)
        val progress = RouteTracker.trackProgress(
            route = testRoute,
            currentLat = 28.6150,
            currentLon = 77.2320, // ~250m east
            speedMps = 10f,
            currentStepIndex = 0
        )

        assertTrue("Should flag off-route when deviation exceeds threshold", progress.isOffRoute)
        assertTrue("Cross-track distance should be > 85m", progress.crossTrackDistanceM > 85f)
    }

    @Test
    fun testHaversineDistanceAccuracy() {
        // Equator 1 degree longitude ~ 111.32 km
        val distM = RouteTracker.distanceM(0.0, 0.0, 0.0, 1.0)
        assertTrue("1 degree lon at equator should be ~111.3 km", distM in 110_000f..112_000f)
    }
}

package com.sih.idr.demo.ui.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

/**
 * Unit tests for pure 3D tunnel corridor projection geometry (D-126).
 *
 * Ensures mathematical consistency of perspective scaling, lateral convergence,
 * vertical depth ordering, and distance clamping without requiring Compose runtime.
 */
class CorridorGeometryTest {

    private val screenWidth = 1080f
    private val screenHeight = 2400f

    @Test
    fun project_pointAtD0SitsBelowPointAtD100OnScreen() {
        // Road surface point at d = 0 m vs d = 100 m
        val p0 = project(dM = 0f, xM = 0f, yM = 0f, w = screenWidth, h = screenHeight)
        val p100 = project(dM = 100f, xM = 0f, yM = 0f, w = screenWidth, h = screenHeight)

        // In screen coordinates, larger Y is lower on screen (below)
        assertTrue(
            "A point on the road at d=0 (y=${p0.y}) must sit below a point at d=100 (y=${p100.y})",
            p0.y > p100.y
        )
    }

    @Test
    fun project_lateralOffsetShrinksWithDistance() {
        val vpX = screenWidth * CorridorGeometry.VP_X_RATIO
        val lateralOffsetM = 3.5f

        val pClose = project(dM = 5f, xM = lateralOffsetM, yM = 0f, w = screenWidth, h = screenHeight)
        val pFar = project(dM = 60f, xM = lateralOffsetM, yM = 0f, w = screenWidth, h = screenHeight)

        val closeOffsetPx = abs(pClose.x - vpX)
        val farOffsetPx = abs(pFar.x - vpX)

        assertTrue(
            "Lateral offset at d=5m ($closeOffsetPx px) must exceed offset at d=60m ($farOffsetPx px)",
            closeOffsetPx > farOffsetPx
        )
    }

    @Test
    fun project_negativeDistanceClamped() {
        // Points behind the camera (d < 0) must be clamped to d = 0 (no inversion behind camera)
        val pNeg = project(dM = -25f, xM = 1.75f, yM = 0.5f, w = screenWidth, h = screenHeight)
        val pZero = project(dM = 0f, xM = 1.75f, yM = 0.5f, w = screenWidth, h = screenHeight)

        assertEquals("Projected X for d < 0 must match d = 0", pZero.x, pNeg.x, 1e-4f)
        assertEquals("Projected Y for d < 0 must match d = 0", pZero.y, pNeg.y, 1e-4f)
    }

    @Test
    fun project_laneWidthAtD0OccupiesExpectedScreenFraction() {
        // Standard 3.5 m lane should occupy 60% of screen width at d = 0
        val pLeft = project(dM = 0f, xM = -CorridorGeometry.LANE_WIDTH_M / 2f, yM = 0f, w = screenWidth, h = screenHeight)
        val pRight = project(dM = 0f, xM = CorridorGeometry.LANE_WIDTH_M / 2f, yM = 0f, w = screenWidth, h = screenHeight)

        val laneWidthPx = pRight.x - pLeft.x
        val expectedPx = screenWidth * CorridorGeometry.LANE_WIDTH_FRACTION

        assertEquals("Lane width at d=0 must be 60% of screen width", expectedPx, laneWidthPx, 1e-3f)
    }

    @Test
    fun project_asymptoteConvergesToVanishingPoint() {
        // At extreme distance (d -> infinity), points converge to vanishing point (vpX, vpY)
        val pInf = project(dM = 100_000f, xM = 10f, yM = 2f, w = screenWidth, h = screenHeight)

        val expectedVpX = screenWidth * CorridorGeometry.VP_X_RATIO
        val expectedVpY = screenHeight * CorridorGeometry.VP_Y_RATIO

        assertEquals("Asymptotic X must approach vpX", expectedVpX, pInf.x, 1.0f)
        assertEquals("Asymptotic Y must approach vpY", expectedVpY, pInf.y, 1.0f)
    }
}

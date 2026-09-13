package com.sih.idr.demo.backend

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * `errorEllipse` is the one piece of arithmetic between a reported covariance and what the map
 * draws, in both flavours. These pin the closed-form eigen-decomposition against cases whose
 * answer is known by inspection, so a sign slip in the orientation cannot survive as a mirrored
 * ellipse that looks plausible on a phone.
 */
class CovarianceTest {

    @Test
    fun isotropicCovarianceIsACircleOfRadiusSigma() {
        val e = errorEllipse(covNorthM2 = 12.25f, covNorthEastM2 = 0f, covEastM2 = 12.25f)
        assertEquals(3.5f, e.semiMajorM, 1e-5f)
        assertEquals(3.5f, e.semiMinorM, 1e-5f)
    }

    @Test
    fun northDominantAxisAlignedCovariancePointsNorth() {
        val e = errorEllipse(covNorthM2 = 16f, covNorthEastM2 = 0f, covEastM2 = 4f)
        assertEquals(4f, e.semiMajorM, 1e-5f)
        assertEquals(2f, e.semiMinorM, 1e-5f)
        assertEquals(0f, e.orientationRad, 1e-6f)
    }

    @Test
    fun eastDominantAxisAlignedCovariancePointsEast() {
        val e = errorEllipse(covNorthM2 = 4f, covNorthEastM2 = 0f, covEastM2 = 16f)
        assertEquals(4f, e.semiMajorM, 1e-5f)
        assertEquals(2f, e.semiMinorM, 1e-5f)
        assertEquals((Math.PI / 2).toFloat(), e.orientationRad, 1e-6f)
    }

    @Test
    fun fullyCorrelatedCovarianceIsAFortyFiveDegreeLine() {
        // [[1, 1], [1, 1]] has eigenvalues 2 and 0 with the major axis along (1, 1).
        val e = errorEllipse(covNorthM2 = 1f, covNorthEastM2 = 1f, covEastM2 = 1f)
        assertEquals(sqrt(2f), e.semiMajorM, 1e-5f)
        assertEquals(0f, e.semiMinorM, 1e-5f)
        assertEquals((Math.PI / 4).toFloat(), e.orientationRad, 1e-6f)
    }

    @Test
    fun negativeCorrelationMirrorsTheOrientation() {
        val e = errorEllipse(covNorthM2 = 1f, covNorthEastM2 = -1f, covEastM2 = 1f)
        assertEquals((-Math.PI / 4).toFloat(), e.orientationRad, 1e-6f)
    }

    @Test
    fun outlineVerticesLieOnTheEllipse() {
        // The lateral-dominant case AGENTS.md describes: a long axis across the direction of
        // travel. Every outline vertex, rotated back into the ellipse frame, must satisfy
        // (u/a)^2 + (v/b)^2 = 1.
        val e = errorEllipse(covNorthM2 = 9f, covNorthEastM2 = 5f, covEastM2 = 25f)
        val c = kotlin.math.cos(e.orientationRad)
        val s = kotlin.math.sin(e.orientationRad)
        for (p in e.outline(count = 36)) {
            val u = p.northM * c + p.eastM * s
            val v = -p.northM * s + p.eastM * c
            val r = (u / e.semiMajorM).let { it * it } + (v / e.semiMinorM).let { it * it }
            assertEquals("vertex off the ellipse", 1f, r, 1e-4f)
        }
    }

    @Test
    fun outlineStartsAtTheMajorAxisTip() {
        val e = errorEllipse(covNorthM2 = 16f, covNorthEastM2 = 0f, covEastM2 = 4f)
        val first = e.outline(count = 8).first()
        assertEquals(4f, first.northM, 1e-5f)
        assertEquals(0f, first.eastM, 1e-5f)
    }

    @Test
    fun aNonPositiveDefiniteCovarianceDegradesInsteadOfThrowing() {
        val e = errorEllipse(covNorthM2 = -1f, covNorthEastM2 = Float.NaN, covEastM2 = 4f)
        assertTrue(e.semiMajorM >= 0f && !e.semiMajorM.isNaN())
        assertTrue(e.semiMinorM >= 0f && !e.semiMinorM.isNaN())
        assertEquals(2f, e.semiMajorM, 1e-5f)
    }

    @Test
    fun theMajorAxisSigmaIsWhatTheMetricCardWouldPrint() {
        // TelemetryState keeps `uncertaintyM` next to the covariance; the producer must keep them
        // consistent. For the demo estimator (isotropic) that means sigma == semiMajor exactly.
        val sigma = 7.25f
        val e = errorEllipse(sigma * sigma, 0f, sigma * sigma)
        assertTrue(abs(e.semiMajorM - sigma) < 1e-5f)
    }
}

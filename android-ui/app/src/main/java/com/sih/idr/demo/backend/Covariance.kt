package com.sih.idr.demo.backend

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * The 1 sigma error ellipse of a 2x2 position covariance, in the filter's (north, east) frame.
 *
 * This file is arithmetic on a covariance the producer already reported, so that the two map
 * flavours draw the same shape from the same numbers and neither owns the maths (D-079: the view
 * computes no physics; turning a matrix into a drawable outline is a projection, not a quantity).
 * It is unit-tested in `app/src/test`.
 *
 * @property semiMajorM 1 sigma along the major axis, metres.
 * @property semiMinorM 1 sigma along the minor axis, metres.
 * @property orientationRad angle of the major axis measured from north towards east, radians,
 *   normalised to (-pi/2, pi/2]: an axis is a line, so 135 degrees and -45 degrees are the same
 *   ellipse and only one spelling is ever returned.
 */
data class ErrorEllipse(
    val semiMajorM: Float,
    val semiMinorM: Float,
    val orientationRad: Float
) {
    /** Outline as (north, east) offsets from the ellipse centre, metres, `count` vertices. */
    fun outline(count: Int = 48): List<TrackPoint> {
        val c = cos(orientationRad)
        val s = sin(orientationRad)
        return List(count) { i ->
            val t = (2.0 * Math.PI * i / count).toFloat()
            val u = semiMajorM * cos(t)
            val v = semiMinorM * sin(t)
            TrackPoint(northM = u * c - v * s, eastM = u * s + v * c)
        }
    }
}

/**
 * Closed-form eigen-decomposition of the symmetric 2x2 matrix `[[nn, ne], [ne, ee]]`.
 *
 * Negative or NaN variances are clamped to zero rather than thrown: a filter can momentarily
 * report a covariance that is not positive semi-definite, and the map should draw a degenerate
 * ellipse for that frame rather than crash the demo.
 */
fun errorEllipse(covNorthM2: Float, covNorthEastM2: Float, covEastM2: Float): ErrorEllipse {
    val nn = sanitise(covNorthM2)
    val ee = sanitise(covEastM2)
    val ne = if (covNorthEastM2.isNaN()) 0f else covNorthEastM2
    val trace = nn + ee
    val diff = nn - ee
    val disc = sqrt(max(0f, diff * diff / 4f + ne * ne))
    val lambdaMajor = max(0f, trace / 2f + disc)
    val lambdaMinor = max(0f, trace / 2f - disc)
    // Major-axis eigenvector of [[nn, ne], [ne, ee]]: (ne, lambdaMajor - nn), or north if ne == 0
    // and nn dominates. atan2 of (east component, north component) gives the bearing from north.
    val raw = when {
        ne != 0f -> atan2(lambdaMajor - nn, ne)
        nn >= ee -> 0f
        else -> (Math.PI / 2).toFloat()
    }
    val halfTurn = Math.PI.toFloat()
    val orientation = when {
        raw > halfTurn / 2f -> raw - halfTurn
        raw <= -halfTurn / 2f -> raw + halfTurn
        else -> raw
    }
    return ErrorEllipse(
        semiMajorM = sqrt(lambdaMajor),
        semiMinorM = sqrt(lambdaMinor),
        orientationRad = orientation
    )
}

private fun sanitise(variance: Float): Float = if (variance.isNaN() || variance < 0f) 0f else variance

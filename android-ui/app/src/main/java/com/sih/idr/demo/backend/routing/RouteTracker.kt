package com.sih.idr.demo.backend.routing

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Result of tracking vehicle progress along a navigation route.
 */
data class RouteProgressResult(
    val stepIndex: Int,
    val distanceToNextStepM: Float,
    val remainingDistanceM: Float,
    val remainingDurationSec: Long,
    val progressFraction: Float,
    val hasArrived: Boolean,
    val isOffRoute: Boolean,
    val crossTrackDistanceM: Float
)

/**
 * Pure, deterministic route tracking engine.
 *
 * Continuously projects vehicle position onto the active route polyline,
 * tracks step-by-step progress, computes dynamic speed-adjusted ETA,
 * advances maneuver steps, and detects destination arrival.
 */
object RouteTracker {

    const val ARRIVAL_DISTANCE_THRESHOLD_M = 25f
    const val STEP_ADVANCE_RADIUS_M = 30f
    const val OFF_ROUTE_THRESHOLD_M = 85f
    private const val DEFAULT_CITY_SPEED_MPS = 8.33f // ~30 km/h city average
    private const val EARTH_RADIUS_M = 6371000.0

    /**
     * Computes real-time progress along [route] from vehicle coordinate ([currentLat], [currentLon]).
     */
    fun trackProgress(
        route: NavigationRoute,
        currentLat: Double,
        currentLon: Double,
        speedMps: Float,
        currentStepIndex: Int = 0
    ): RouteProgressResult {
        val points = route.points
        val steps = route.steps
        val dest = route.destinationCoord

        // 1. Direct distance to final destination
        val distToDestM = distanceM(currentLat, currentLon, dest.latitude, dest.longitude)
        if (distToDestM <= ARRIVAL_DISTANCE_THRESHOLD_M) {
            return RouteProgressResult(
                stepIndex = max(0, steps.size - 1),
                distanceToNextStepM = 0f,
                remainingDistanceM = 0f,
                remainingDurationSec = 0L,
                progressFraction = 1.0f,
                hasArrived = true,
                isOffRoute = false,
                crossTrackDistanceM = 0f
            )
        }

        if (points.size < 2) {
            val dist = distToDestM
            val duration = calculateDuration(dist, speedMps)
            return RouteProgressResult(
                stepIndex = 0,
                distanceToNextStepM = dist,
                remainingDistanceM = dist,
                remainingDurationSec = duration,
                progressFraction = 0f,
                hasArrived = false,
                isOffRoute = false,
                crossTrackDistanceM = 0f
            )
        }

        // 2. Find closest segment on the route polyline
        var minCrossTrackDistM = Float.MAX_VALUE
        var closestSegmentIndex = 0
        var closestFractionAlongSegment = 0f

        for (i in 0 until points.size - 1) {
            val p1 = points[i]
            val p2 = points[i + 1]

            val (distM, t) = projectPointToSegment(currentLat, currentLon, p1, p2)
            if (distM < minCrossTrackDistM) {
                minCrossTrackDistM = distM
                closestSegmentIndex = i
                closestFractionAlongSegment = t
            }
        }

        val isOffRoute = minCrossTrackDistM > OFF_ROUTE_THRESHOLD_M

        // 3. Calculate remaining distance along polyline from projection point to destination
        val p1 = points[closestSegmentIndex]
        val p2 = points[closestSegmentIndex + 1]
        val segLengthM = distanceM(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
        val remainingOnCurrentSegment = segLengthM * (1f - closestFractionAlongSegment)

        var polylineRemainingM = remainingOnCurrentSegment
        for (i in (closestSegmentIndex + 1) until (points.size - 1)) {
            val a = points[i]
            val b = points[i + 1]
            polylineRemainingM += distanceM(a.latitude, a.longitude, b.latitude, b.longitude)
        }

        // Bound remaining distance so it cannot exceed route total or go below 0
        val remainingDistanceM = polylineRemainingM.coerceIn(0f, route.distanceMeters * 1.5f)
        val progressFraction = if (route.distanceMeters > 0f) {
            (1f - (remainingDistanceM / route.distanceMeters)).coerceIn(0f, 1f)
        } else {
            0f
        }

        // 4. Determine active step index & distance to next maneuver
        var stepIndex = currentStepIndex.coerceIn(0, max(0, steps.size - 1))
        var distToNextStepM = 0f

        if (steps.isNotEmpty()) {
            val currentStep = steps[stepIndex]
            val stepCoord = currentStep.coordinate
            val straightDistToStep = distanceM(currentLat, currentLon, stepCoord.latitude, stepCoord.longitude)

            // If close to the maneuver point, advance to next step
            if (straightDistToStep <= STEP_ADVANCE_RADIUS_M && stepIndex < steps.size - 1) {
                stepIndex++
                val nextStep = steps[stepIndex]
                distToNextStepM = distanceM(currentLat, currentLon, nextStep.coordinate.latitude, nextStep.coordinate.longitude)
            } else {
                distToNextStepM = straightDistToStep
            }
        }

        val dynamicDurationSec = calculateDuration(remainingDistanceM, speedMps)
        val hasArrived = remainingDistanceM <= ARRIVAL_DISTANCE_THRESHOLD_M || distToDestM <= ARRIVAL_DISTANCE_THRESHOLD_M

        return RouteProgressResult(
            stepIndex = stepIndex,
            distanceToNextStepM = if (hasArrived) 0f else distToNextStepM,
            remainingDistanceM = if (hasArrived) 0f else remainingDistanceM,
            remainingDurationSec = if (hasArrived) 0L else dynamicDurationSec,
            progressFraction = if (hasArrived) 1.0f else progressFraction,
            hasArrived = hasArrived,
            isOffRoute = isOffRoute,
            crossTrackDistanceM = minCrossTrackDistM
        )
    }

    private fun calculateDuration(distanceM: Float, speedMps: Float): Long {
        val effectiveSpeed = if (speedMps >= 2.0f) speedMps else DEFAULT_CITY_SPEED_MPS
        return (distanceM / effectiveSpeed).toLong().coerceAtLeast(10L)
    }

    /**
     * Distance in metres between two WGS84 geographic coordinates using Haversine.
     */
    fun distanceM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Float {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
            sin(dLon / 2) * sin(dLon / 2)
        val c = 2 * atan2(sqrt(a), sqrt(max(0.0, 1.0 - a)))
        return (EARTH_RADIUS_M * c).toFloat()
    }

    /**
     * Projects a point (lat, lon) onto segment (p1 -> p2).
     * Returns Pair(distanceInMeters, tFractionClamped0to1).
     */
    private fun projectPointToSegment(
        lat: Double,
        lon: Double,
        p1: GeoCoordinate,
        p2: GeoCoordinate
    ): Pair<Float, Float> {
        val latPerMetre = 1.0 / 111_320.0
        val lonPerMetre = 1.0 / (111_320.0 * cos(Math.toRadians(p1.latitude)))

        // Flat-earth local projection for segment distance
        val x = (lon - p1.longitude) / lonPerMetre
        val y = (lat - p1.latitude) / latPerMetre

        val dx = (p2.longitude - p1.longitude) / lonPerMetre
        val dy = (p2.latitude - p1.latitude) / latPerMetre

        val segLenSq = dx * dx + dy * dy
        if (segLenSq < 1e-4) {
            val dist = distanceM(lat, lon, p1.latitude, p1.longitude)
            return Pair(dist, 0f)
        }

        val t = ((x * dx + y * dy) / segLenSq).toFloat().coerceIn(0f, 1f)
        val projLat = p1.latitude + t * (p2.latitude - p1.latitude)
        val projLon = p1.longitude + t * (p2.longitude - p1.longitude)

        val dist = distanceM(lat, lon, projLat, projLon)
        return Pair(dist, t)
    }
}

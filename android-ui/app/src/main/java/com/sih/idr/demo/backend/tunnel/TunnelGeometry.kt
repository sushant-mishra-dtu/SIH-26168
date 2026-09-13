package com.sih.idr.demo.backend.tunnel

import kotlin.math.cos
import kotlin.math.sqrt

/**
 * Geographic coordinate pair (latitude, longitude) in degrees.
 */
data class LatLon(val lat: Double, val lon: Double)

/**
 * Definition of a tunnel corridor and its centreline geometry (D-126).
 *
 * @property id Unique stable identifier (e.g. "demo-tunnel-1").
 * @property name Human-readable name.
 * @property centreline Ordered centreline vertices, entry portal first; at least 2 points.
 * @property lengthM Cumulative centreline length in metres.
 * @property postedLimitKmh Speed limit in km/h if declared, or null if unknown.
 */
data class TunnelDef(
    val id: String,
    val name: String,
    val centreline: List<LatLon>,
    val lengthM: Double,
    val postedLimitKmh: Int?
)

/**
 * Projection of a vehicle coordinate onto a tunnel centreline (D-126).
 *
 * @property tunnel The tunnel matched.
 * @property alongM Distance along the centreline from the entry portal, metres. Can be negative
 *   before entry or greater than length past exit.
 * @property remainingM Remaining distance to the exit portal, metres (lengthM - alongM).
 * @property lateralM Perpendicular distance from the matched centreline segment line, metres.
 * @property distanceToEntryM Direct flat-earth distance to the first centreline point when outside,
 *   else 0.0 when inside.
 * @property inside True when lateralM <= maxLateralM AND 0.0 <= alongM <= lengthM.
 */
data class TunnelFix(
    val tunnel: TunnelDef,
    val alongM: Double,
    val remainingM: Double,
    val lateralM: Double,
    val distanceToEntryM: Double,
    val inside: Boolean
)

/**
 * Metres per degree of latitude, matching LocalNavigationEstimator's flat-earth assumption.
 */
private const val METRES_PER_LAT_DEG = 111_320.0

/**
 * Flat-earth distance in metres between two LatLon points using cos(lat) scaling about
 * their midpoint -- the exact same assumption LocalNavigationEstimator makes for local metric
 * displacements (D-126).
 */
fun distanceM(p1: LatLon, p2: LatLon): Double {
    val midLat = (p1.lat + p2.lat) / 2.0
    val dN = (p2.lat - p1.lat) * METRES_PER_LAT_DEG
    val dE = (p2.lon - p1.lon) * METRES_PER_LAT_DEG * cos(Math.toRadians(midLat))
    return sqrt(dN * dN + dE * dE)
}

/**
 * Computes cumulative length in metres along an ordered list of centreline points.
 */
fun computeCentrelineLengthM(centreline: List<LatLon>): Double {
    if (centreline.size < 2) return 0.0
    var total = 0.0
    for (i in 0 until centreline.size - 1) {
        total += distanceM(centreline[i], centreline[i + 1])
    }
    return total
}

/**
 * Translates a TunnelFix into the portal distance expected by TunnelFsm.onPortalDistance (D-126).
 *
 * Returns distanceToEntryM when outside and within 500 m of entry, remainingM when inside,
 * null otherwise (past exit, beyond 500 m, or no fix).
 */
fun portalDistanceM(fix: TunnelFix?): Float? {
    if (fix == null) return null
    if (fix.inside) return fix.remainingM.toFloat()
    if (fix.alongM <= fix.tunnel.lengthM && fix.distanceToEntryM <= 500.0) {
        return fix.distanceToEntryM.toFloat()
    }
    return null
}

/**
 * Pure Kotlin tunnel geometry locator (D-126).
 *
 * Evaluates vehicle positions against declared tunnel centrelines without requiring
 * external map SDKs or network connections.
 */
class TunnelGeometry(val tunnels: List<TunnelDef>) {

    /**
     * Projects a (lat, lon) point onto the nearest centreline segment using a local flat-earth
     * metre frame about the segment with cos(lat) scaling -- identical to LocalNavigationEstimator.
     *
     * @param lat Vehicle latitude in degrees.
     * @param lon Vehicle longitude in degrees.
     * @param maxLateralM Maximum perpendicular distance in metres to be considered inside the bore.
     * @return Closest [TunnelFix], or null if no tunnels are configured or coordinates are invalid.
     */
    fun locate(lat: Double, lon: Double, maxLateralM: Double = 30.0): TunnelFix? {
        if (tunnels.isEmpty() || lat.isNaN() || lon.isNaN()) return null

        val candidateFixes = tunnels.mapNotNull { tunnel ->
            locateInTunnel(tunnel, lat, lon, maxLateralM)
        }
        if (candidateFixes.isEmpty()) return null

        // Prefer a tunnel the vehicle is inside; if multiple, pick the one with lowest lateral offset.
        val insideFix = candidateFixes.filter { it.inside }.minByOrNull { it.lateralM }
        if (insideFix != null) return insideFix

        // Otherwise pick the tunnel closest to the vehicle (by distance to entry portal).
        return candidateFixes.minByOrNull { it.distanceToEntryM }
    }

    private fun locateInTunnel(
        tunnel: TunnelDef,
        lat: Double,
        lon: Double,
        maxLateralM: Double
    ): TunnelFix? {
        val points = tunnel.centreline
        if (points.size < 2) return null

        var bestDistToSegment = Double.POSITIVE_INFINITY
        var bestAlongM = 0.0
        var bestLateralM = 0.0
        var cumDist = 0.0

        for (i in 0 until points.size - 1) {
            val p1 = points[i]
            val p2 = points[i + 1]
            val midLat = (p1.lat + p2.lat) / 2.0
            val cosLat = cos(Math.toRadians(midLat))

            val dN = (p2.lat - p1.lat) * METRES_PER_LAT_DEG
            val dE = (p2.lon - p1.lon) * METRES_PER_LAT_DEG * cosLat
            val segLen = sqrt(dN * dN + dE * dE)

            if (segLen <= 0.0) {
                cumDist += segLen
                continue
            }

            val uN = dN / segLen
            val uE = dE / segLen

            val qN = (lat - p1.lat) * METRES_PER_LAT_DEG
            val qE = (lon - p1.lon) * METRES_PER_LAT_DEG * cosLat

            // Projection along segment line from p1
            val s = qN * uN + qE * uE

            // Perpendicular vector and distance to the infinite segment line
            val perpN = qN - s * uN
            val perpE = qE - s * uE
            val perpDist = sqrt(perpN * perpN + perpE * perpE)

            // Distance to finite segment clamped in [0, segLen]
            val t = s.coerceIn(0.0, segLen)
            val clampN = qN - t * uN
            val clampE = qE - t * uE
            val distToSegment = sqrt(clampN * clampN + clampE * clampE)

            if (distToSegment < bestDistToSegment) {
                bestDistToSegment = distToSegment
                bestAlongM = cumDist + s
                bestLateralM = perpDist
            }

            cumDist += segLen
        }

        if (bestDistToSegment.isInfinite()) return null

        val alongM = bestAlongM
        val remainingM = tunnel.lengthM - alongM
        val lateralM = bestLateralM
        val inside = lateralM <= maxLateralM && alongM >= 0.0 && alongM <= tunnel.lengthM
        val distanceToEntryM = if (inside) 0.0 else distanceM(points.first(), LatLon(lat, lon))

        return TunnelFix(
            tunnel = tunnel,
            alongM = alongM,
            remainingM = remainingM,
            lateralM = lateralM,
            distanceToEntryM = distanceToEntryM,
            inside = inside
        )
    }
}

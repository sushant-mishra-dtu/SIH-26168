package com.sih.idr.demo.backend.routing

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.roundToInt

/**
 * 2D geographical coordinate representation.
 */
data class GeoCoordinate(
    val latitude: Double,
    val longitude: Double
)

/**
 * Standard turn-by-turn navigation maneuver types.
 */
enum class ManeuverType {
    STRAIGHT,
    TURN_RIGHT,
    TURN_LEFT,
    SLIGHT_RIGHT,
    SLIGHT_LEFT,
    UTURN,
    TUNNEL_ENTRY,
    TUNNEL_EXIT,
    ARRIVE
}

/**
 * Single turn-by-turn maneuver instruction along an active route.
 */
data class RouteManeuver(
    val instruction: String,
    val distanceM: Float,
    val maneuverType: ManeuverType,
    val coordinate: GeoCoordinate,
    val streetName: String? = null
)

/**
 * Active navigation route geometry, maneuver steps, and ETA metadata.
 */
data class NavigationRoute(
    val destinationName: String,
    val destinationCoord: GeoCoordinate,
    val distanceMeters: Float,
    val durationSeconds: Long,
    val points: List<GeoCoordinate>,
    val steps: List<RouteManeuver> = emptyList()
) {
    /** Formatted human-readable ETA (e.g., "14 min", "1 hr 12 min"). */
    val formattedEta: String
        get() {
            val minutes = (durationSeconds / 60).coerceAtLeast(1)
            return if (minutes < 60) {
                "$minutes min"
            } else {
                val hours = minutes / 60
                val remMin = minutes % 60
                if (remMin > 0) "$hours hr $remMin min" else "$hours hr"
            }
        }

    /** Formatted distance remaining (e.g., "450 m", "8.2 km"). */
    val formattedDistance: String
        get() {
            return if (distanceMeters < 1000f) {
                "${distanceMeters.roundToInt()} m"
            } else {
                val km = distanceMeters / 1000f
                "%.1f km".format(Locale.US, km)
            }
        }

    /** Formatted clock arrival time (e.g., "10:25 PM"). */
    val formattedArrivalTime: String
        get() {
            val arrivalEpochMs = System.currentTimeMillis() + (durationSeconds * 1000L)
            val sdf = SimpleDateFormat("h:mm a", Locale.getDefault())
            return sdf.format(Date(arrivalEpochMs))
        }
}

package com.sih.idr.demo.backend.routing

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * Navigation routing and destination search service.
 * Connects to OpenStreetMap Nominatim for geocoding and OSRM for driving routes,
 * with deterministic offline fallback to pre-surveyed corridor geometry.
 */
object RouteService {

    private const val USER_AGENT = "IDR-Navigator/1.0 (SIH-26168 Intelligent Dead Reckoning)"
    private const val CONNECT_TIMEOUT_MS = 2500
    private const val READ_TIMEOUT_MS = 3000

    /**
     * Searches for destinations matching [query], combining pre-cached presets and online results.
     *
     * Thin delegating wrapper around [GeocodingService.search]; all geocoding logic lives there.
     * Kept here so existing call sites in [DestinationSearchBar] and tests compile without change.
     */
    suspend fun searchLocations(
        query: String,
        userLat: Double,
        userLon: Double,
        category: String = "All"
    ): List<SearchItem> {
        // Map the UI category pill to an OSM tag filter for online search
        val osmTagFilter: String? = when (category) {
            "Fuel"      -> "amenity=fuel"
            "Food"      -> "amenity=restaurant"
            "Parking"   -> "amenity=parking"
            "Hospitals" -> "amenity=hospital"
            else        -> null      // All / Tunnels / Airports / Landmarks — no tag restriction
        }
        return GeocodingService.default.search(query, userLat, userLon, osmTagFilter)
    }

    /**
     * Generates a turn-by-turn [NavigationRoute] from [start] to [destination].
     * Fetches driving route from OSRM, falling back to a direct interpolated corridor if offline.
     */
    suspend fun fetchRoute(
        start: GeoCoordinate,
        destination: SearchItem
    ): NavigationRoute = withContext(Dispatchers.IO) {
        val destCoord = destination.coordinate
        try {
            val urlString = "https://router.project-osrm.org/route/v1/driving/" +
                "${start.longitude},${start.latitude};${destCoord.longitude},${destCoord.latitude}" +
                "?overview=full&geometries=geojson&steps=true"
            val url = URL(urlString)
            val connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                setRequestProperty("User-Agent", USER_AGENT)
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
            }

            if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                val reader = BufferedReader(InputStreamReader(connection.inputStream))
                val response = reader.use { it.readText() }
                connection.disconnect()

                val root = JSONObject(response)
                val routes = root.optJSONArray("routes")
                if (routes != null && routes.length() > 0) {
                    val routeObj = routes.getJSONObject(0)
                    val distanceM = routeObj.optDouble("distance", 0.0).toFloat()
                    val durationS = routeObj.optDouble("duration", 0.0).toLong()

                    // Extract path coordinates
                    val geom = routeObj.optJSONObject("geometry")
                    val coordsArray = geom?.optJSONArray("coordinates")
                    val points = ArrayList<GeoCoordinate>()
                    if (coordsArray != null) {
                        for (i in 0 until coordsArray.length()) {
                            val pt = coordsArray.getJSONArray(i)
                            points.add(GeoCoordinate(latitude = pt.getDouble(1), longitude = pt.getDouble(0)))
                        }
                    }

                    // Extract maneuvers
                    val maneuvers = ArrayList<RouteManeuver>()
                    val legs = routeObj.optJSONArray("legs")
                    if (legs != null && legs.length() > 0) {
                        val steps = legs.getJSONObject(0).optJSONArray("steps")
                        if (steps != null) {
                            for (s in 0 until steps.length()) {
                                val step = steps.getJSONObject(s)
                                val stepDist = step.optDouble("distance", 0.0).toFloat()
                                val stepName = step.optString("name", "")
                                val manObj = step.optJSONObject("maneuver")
                                val manTypeStr = manObj?.optString("type", "") ?: ""
                                val modifier = manObj?.optString("modifier", "") ?: ""

                                val type = parseManeuverType(manTypeStr, modifier, destination.isTunnel)
                                val instruction = formatInstruction(type, stepName, modifier)
                                val locArray = manObj?.optJSONArray("location")
                                val coord = if (locArray != null && locArray.length() >= 2) {
                                    GeoCoordinate(locArray.getDouble(1), locArray.getDouble(0))
                                } else {
                                    start
                                }

                                maneuvers.add(
                                    RouteManeuver(
                                        instruction = instruction,
                                        distanceM = stepDist,
                                        maneuverType = type,
                                        coordinate = coord,
                                        streetName = stepName.ifEmpty { null }
                                    )
                                )
                            }
                        }
                    }

                    if (points.isNotEmpty()) {
                        return@withContext NavigationRoute(
                            destinationName = destination.title,
                            destinationCoord = destCoord,
                            distanceMeters = distanceM,
                            durationSeconds = durationS,
                            points = points,
                            steps = maneuvers
                        )
                    }
                }
            }
            connection.disconnect()
        } catch (_: Exception) {
            // Fall through to deterministic offline route synthesizer
        }

        // Offline / fallback corridor route
        createFallbackRoute(start, destination)
    }

    private fun parseManeuverType(type: String, modifier: String, isTunnel: Boolean): ManeuverType {
        return when {
            type == "arrive" -> ManeuverType.ARRIVE
            isTunnel && (modifier.contains("tunnel") || type.contains("tunnel")) -> ManeuverType.TUNNEL_ENTRY
            modifier.contains("slight right") -> ManeuverType.SLIGHT_RIGHT
            modifier.contains("slight left") -> ManeuverType.SLIGHT_LEFT
            modifier.contains("right") -> ManeuverType.TURN_RIGHT
            modifier.contains("left") -> ManeuverType.TURN_LEFT
            modifier.contains("u-turn") || modifier.contains("uturn") -> ManeuverType.UTURN
            else -> ManeuverType.STRAIGHT
        }
    }

    private fun formatInstruction(type: ManeuverType, street: String, modifier: String): String {
        val target = if (street.isNotEmpty()) "onto $street" else "ahead"
        return when (type) {
            ManeuverType.TURN_RIGHT -> "Turn right $target"
            ManeuverType.TURN_LEFT -> "Turn left $target"
            ManeuverType.SLIGHT_RIGHT -> "Keep right $target"
            ManeuverType.SLIGHT_LEFT -> "Keep left $target"
            ManeuverType.UTURN -> "Make a U-turn $target"
            ManeuverType.TUNNEL_ENTRY -> "Enter tunnel corridor $target"
            ManeuverType.TUNNEL_EXIT -> "Exit tunnel corridor"
            ManeuverType.ARRIVE -> "Arrive at destination"
            ManeuverType.STRAIGHT -> if (modifier.isNotEmpty()) "Continue $modifier $target" else "Continue straight $target"
        }
    }

    private fun createFallbackRoute(start: GeoCoordinate, destination: SearchItem): NavigationRoute {
        val destCoord = destination.coordinate
        val distanceM = SearchPreset.distanceBetweenM(
            start.latitude,
            start.longitude,
            destCoord.latitude,
            destCoord.longitude
        )

        // Interpolate points between start and destination for map polyline rendering
        val stepsCount = 16
        val points = ArrayList<GeoCoordinate>(stepsCount + 1)
        for (i in 0..stepsCount) {
            val fraction = i.toDouble() / stepsCount
            val lat = start.latitude + (destCoord.latitude - start.latitude) * fraction
            val lon = start.longitude + (destCoord.longitude - start.longitude) * fraction
            points.add(GeoCoordinate(lat, lon))
        }

        // 30 km/h average speed in city traffic (8.33 m/s)
        val durationS = ((distanceM / 8.33f).toLong()).coerceAtLeast(30L)

        val maneuvers = mutableListOf<RouteManeuver>()
        if (destination.isTunnel) {
            maneuvers.add(
                RouteManeuver(
                    instruction = "Head toward ${destination.title}",
                    distanceM = distanceM * 0.3f,
                    maneuverType = ManeuverType.STRAIGHT,
                    coordinate = start,
                    streetName = "Corridor Approach"
                )
            )
            maneuvers.add(
                RouteManeuver(
                    instruction = "Enter ${destination.title}",
                    distanceM = distanceM * 0.6f,
                    maneuverType = ManeuverType.TUNNEL_ENTRY,
                    coordinate = points[stepsCount / 3],
                    streetName = destination.title
                )
            )
            maneuvers.add(
                RouteManeuver(
                    instruction = "Exit tunnel toward destination",
                    distanceM = distanceM * 0.1f,
                    maneuverType = ManeuverType.TUNNEL_EXIT,
                    coordinate = points[(stepsCount * 2) / 3]
                )
            )
        } else {
            maneuvers.add(
                RouteManeuver(
                    instruction = "Head toward ${destination.title}",
                    distanceM = distanceM * 0.7f,
                    maneuverType = ManeuverType.STRAIGHT,
                    coordinate = start
                )
            )
        }
        maneuvers.add(
            RouteManeuver(
                instruction = "Arrive at ${destination.title}",
                distanceM = 0f,
                maneuverType = ManeuverType.ARRIVE,
                coordinate = destCoord
            )
        )

        return NavigationRoute(
            destinationName = destination.title,
            destinationCoord = destCoord,
            distanceMeters = distanceM,
            durationSeconds = durationS,
            points = points,
            steps = maneuvers
        )
    }
}

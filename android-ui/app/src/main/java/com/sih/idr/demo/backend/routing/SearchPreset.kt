package com.sih.idr.demo.backend.routing

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Pre-cached landmark or search destination item.
 */
data class SearchItem(
    val id: String,
    val title: String,
    val subtitle: String,
    val category: String,
    val coordinate: GeoCoordinate,
    val isTunnel: Boolean = false,
    val postedLimitKmh: Int? = null
)

/**
 * Curated destination presets for Delhi NCR with pre-surveyed coordinates.
 * Provides instantaneous search without requiring an active network connection.
 */
object SearchPreset {

    val CATEGORIES = listOf("All", "Tunnels", "Airports", "Landmarks")

    val PRESETS = listOf(
        SearchItem(
            id = "pragati_tunnel",
            title = "Pragati Maidan Tunnel",
            subtitle = "Bhairon Marg to Ring Road / Mathura Rd",
            category = "Tunnels",
            coordinate = GeoCoordinate(latitude = 28.6185, longitude = 77.2415),
            isTunnel = true,
            postedLimitKmh = 50
        ),
        SearchItem(
            id = "igi_airport_t3",
            title = "IGI Airport Terminal 3",
            subtitle = "Indira Gandhi International Airport, New Delhi",
            category = "Airports",
            coordinate = GeoCoordinate(latitude = 28.5562, longitude = 77.1000)
        ),
        SearchItem(
            id = "connaught_place",
            title = "Connaught Place (Inner Circle)",
            subtitle = "Rajiv Chowk, Central Delhi",
            category = "Landmarks",
            coordinate = GeoCoordinate(latitude = 28.6315, longitude = 77.2167)
        ),
        SearchItem(
            id = "india_gate",
            title = "India Gate",
            subtitle = "Kartavya Path, New Delhi",
            category = "Landmarks",
            coordinate = GeoCoordinate(latitude = 28.6129, longitude = 77.2295)
        ),
        SearchItem(
            id = "aiims_delhi",
            title = "AIIMS New Delhi",
            subtitle = "Sri Aurobindo Marg, Ansari Nagar",
            category = "Landmarks",
            coordinate = GeoCoordinate(latitude = 28.5672, longitude = 77.2100)
        ),
        SearchItem(
            id = "cyber_hub",
            title = "DLF Cyber Hub",
            subtitle = "Cyber City, DLF Phase 2, Gurugram",
            category = "Landmarks",
            coordinate = GeoCoordinate(latitude = 28.4950, longitude = 77.0895)
        ),
        SearchItem(
            id = "aerocity",
            title = "Delhi Aerocity",
            subtitle = "Hospitality District, Near IGI Airport",
            category = "Airports",
            coordinate = GeoCoordinate(latitude = 28.5505, longitude = 77.1215)
        )
    )

    /**
     * Filters presets based on user query and optional category filter, sorted by distance.
     */
    fun findPresets(
        query: String,
        category: String = "All",
        userLat: Double = 28.6129,
        userLon: Double = 77.2295
    ): List<SearchItem> {
        val q = query.trim().lowercase()
        return PRESETS.filter { item ->
            val matchesCategory = (category == "All" || item.category.equals(category, ignoreCase = true))
            val matchesQuery = q.isEmpty() ||
                item.title.lowercase().contains(q) ||
                item.subtitle.lowercase().contains(q)
            matchesCategory && matchesQuery
        }.sortedBy { item ->
            distanceBetweenM(userLat, userLon, item.coordinate.latitude, item.coordinate.longitude)
        }
    }

    /**
     * Computes spherical distance in metres between two points.
     */
    fun distanceBetweenM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Float {
        val earthRadiusM = 6371000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
            sin(dLon / 2) * sin(dLon / 2)
        val c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return (earthRadiusM * c).toFloat()
    }
}

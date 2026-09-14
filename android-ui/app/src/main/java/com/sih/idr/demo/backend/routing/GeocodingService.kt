package com.sih.idr.demo.backend.routing

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import kotlin.math.roundToInt

/**
 * Destination geocoding service for the IDR Navigator.
 *
 * **Primary: Photon** (`photon.komoot.io`) — built for autocomplete, supports prefix
 * matching, and biases results toward the user position. Parses GeoJSON features.
 *
 * **Fallback: Nominatim** — only when Photon fails or returns nothing, only for queries
 * >= 3 chars. Throttled to at most one call per second to comply with the public usage policy.
 *
 * Every failure path returns the offline preset list rather than throwing, so the search bar
 * always has something to show and never crashes.
 *
 * @param fetcher Injectable HTTP layer — supply a `(String) -> String` lambda in tests to use
 *   canned JSON without any real network. The default calls [defaultFetch].
 * @param presets Offline preset list; injectable so tests can assert against a fixed catalogue.
 */
class GeocodingService(
    private val fetcher: (String) -> String = ::defaultFetch,
    private val presets: List<SearchItem> = SearchPreset.PRESETS
) {

    /** Epoch-ms of the last Nominatim call; enforces the 1-call/sec usage policy. */
    @Volatile private var lastNominatimCallMs: Long = 0L

    // ────────────────────────────────────────────────────────────────────────
    // Public API
    // ────────────────────────────────────────────────────────────────────────

    /**
     * Searches for destinations matching [query] with proximity bias toward ([userLat],[userLon]).
     *
     * Pipeline:
     * 1. Photon (prefix autocomplete, any query length, `countrycode=in` filter)
     * 2. Nominatim (full-text, only when Photon fails, only for query.length >= 3)
     * 3. Offline presets on any failure — never throws, always returns something
     *
     * @param osmTagFilter Optional OSM tag constraint passed to Photon, e.g. "amenity=fuel".
     */
    suspend fun search(
        query: String,
        userLat: Double,
        userLon: Double,
        osmTagFilter: String? = null
    ): List<SearchItem> = withContext(Dispatchers.IO) {
        val trimmed = query.trim()
        val q = trimmed.lowercase()
        val offlineResults = presets.filter { item ->
            q.isEmpty() || item.title.lowercase().contains(q) || item.subtitle.lowercase().contains(q)
        }.sortedBy { item ->
            SearchPreset.distanceBetweenM(userLat, userLon, item.coordinate.latitude, item.coordinate.longitude)
        }.map { it.copy(source = SearchSource.PRESET) }

        val photonResults = runCatching {
            fetchPhoton(trimmed, userLat, userLon, osmTagFilter)
        }.getOrNull() ?: emptyList()

        val onlineResults: List<SearchItem> = when {
            photonResults.isNotEmpty() -> photonResults
            trimmed.length >= 3 -> runCatching {
                throttleNominatim()
                fetchNominatim(trimmed, userLat, userLon)
            }.getOrNull() ?: emptyList()
            else -> emptyList()
        }

        mergeAndRank(offlineResults, onlineResults, trimmed, userLat, userLon)
    }

    /**
     * Nearby POI search for a selected category pill with an empty query.
     *
     * This is Photon's `/reverse` with a tag filter and a radius, which returns the POIs of that
     * kind nearest to the point, nearest first. It is not `/api`: that endpoint refuses a request
     * without `q` (HTTP 400, "q parameter is required"), so a nearby search routed through it
     * would silently return nothing every time.
     */
    suspend fun nearby(
        userLat: Double,
        userLon: Double,
        osmTag: String
    ): List<SearchItem> = withContext(Dispatchers.IO) {
        runCatching {
            val url = "https://photon.komoot.io/reverse" +
                "?lat=$userLat&lon=$userLon&osm_tag=${photonTagParam(osmTag)}" +
                "&radius=$NEARBY_RADIUS_KM&limit=10&lang=en"
            parsePhotonGeoJson(fetcher(url))
        }.getOrDefault(emptyList())
    }

    /**
     * Reverse geocodes a map long-press coordinate to a human-readable place name.
     * Returns `null` silently on any network failure so the caller falls back to the
     * coordinate-string name without crashing.
     */
    suspend fun reverse(lat: Double, lon: Double): SearchItem? = withContext(Dispatchers.IO) {
        // Try Photon /reverse first
        val photonResult = runCatching {
            val url = "https://photon.komoot.io/reverse?lat=$lat&lon=$lon"
            parsePhotonGeoJson(fetcher(url)).firstOrNull()
        }.getOrNull()

        if (photonResult != null) {
            return@withContext photonResult.copy(
                id = "pin_${lat.fmt5}_${lon.fmt5}",
                source = SearchSource.PIN
            )
        }

        // Nominatim /reverse fallback
        runCatching {
            val url = "https://nominatim.openstreetmap.org/reverse" +
                "?format=json&lat=$lat&lon=$lon&zoom=18"
            val json = JSONObject(fetcher(url))
            val display = json.optString("display_name", "")
            if (display.isBlank()) return@withContext null
            val parts = display.split(",")
            val title = parts.firstOrNull()?.trim() ?: display
            val subtitle = parts.drop(1).take(3).joinToString(", ") { it.trim() }
            SearchItem(
                id = "pin_${lat.fmt5}_${lon.fmt5}",
                title = title,
                subtitle = subtitle,
                category = "Landmarks",
                coordinate = GeoCoordinate(lat, lon),
                source = SearchSource.PIN
            )
        }.getOrNull()
    }

    // ────────────────────────────────────────────────────────────────────────
    // Private helpers
    // ────────────────────────────────────────────────────────────────────────

    private fun fetchPhoton(
        query: String,
        userLat: Double,
        userLon: Double,
        osmTagFilter: String?
    ): List<SearchItem> {
        val q = URLEncoder.encode(query, "UTF-8")
        val tagParam = osmTagFilter?.let { "&osm_tag=${photonTagParam(it)}" } ?: ""
        val url = "https://photon.komoot.io/api/" +
            "?q=$q&lat=$userLat&lon=$userLon&limit=10&lang=en$tagParam"
        return parsePhotonGeoJson(fetcher(url))
    }

    /**
     * Photon's tag filter is `key:value`, not the `key=value` this app uses for [SearchItem.osmKind]
     * and the category pills. Sent with the `=`, Photon reads the whole string as a key, matches
     * nothing, and every filtered search comes back empty -- checked against the public instance.
     */
    private fun photonTagParam(osmTag: String): String =
        URLEncoder.encode(osmTag.replaceFirst('=', ':'), "UTF-8")

    private fun fetchNominatim(query: String, userLat: Double, userLon: Double): List<SearchItem> {
        val q = URLEncoder.encode(query, "UTF-8")
        // viewbox: lonMin,latMax,lonMax,latMin (not bounded=1 — far-away exact matches still appear)
        val lonMin = userLon - 0.5; val latMax = userLat + 0.5
        val lonMax = userLon + 0.5; val latMin = userLat - 0.5
        val url = "https://nominatim.openstreetmap.org/search" +
            "?format=json&q=$q&countrycodes=in&limit=10" +
            "&viewbox=$lonMin,$latMax,$lonMax,$latMin" +
            "&addressdetails=1&dedupe=1"
        val json = JSONArray(fetcher(url))
        val results = mutableListOf<SearchItem>()
        for (i in 0 until json.length()) {
            val obj = json.getJSONObject(i)
            val display = obj.optString("display_name", "")
            val parts = display.split(",")
            val title = parts.firstOrNull()?.trim() ?: display
            val subtitle = parts.drop(1).take(3).joinToString(", ") { it.trim() }
            val lat = obj.optDouble("lat", Double.NaN)
            val lon = obj.optDouble("lon", Double.NaN)
            if (lat.isNaN() || lon.isNaN()) continue
            results += SearchItem(
                id = "nom_${obj.optString("osm_id", i.toString())}",
                title = title,
                subtitle = subtitle,
                category = "Search",
                coordinate = GeoCoordinate(lat, lon),
                source = SearchSource.ONLINE
            )
        }
        return results
    }

    /**
     * Parses a Photon GeoJSON FeatureCollection.
     *
     * GeoJSON `geometry.coordinates` order is **[longitude, latitude]** — index 0 is lon, 1 is lat.
     * Getting them backwards would silently place every result in the wrong hemisphere.
     */
    private fun parsePhotonGeoJson(json: String): List<SearchItem> {
        val root = JSONObject(json)
        val features = root.optJSONArray("features") ?: return emptyList()
        val results = mutableListOf<SearchItem>()
        for (i in 0 until features.length()) {
            val feat = features.getJSONObject(i)
            val props = feat.optJSONObject("properties") ?: continue

            // Drop non-India results (Photon does not support countrycodes= query param)
            if (!props.optString("countrycode", "").equals("in", ignoreCase = true)) continue

            // GeoJSON: coordinates[0] = longitude, coordinates[1] = latitude
            val coords = feat.optJSONObject("geometry")?.optJSONArray("coordinates") ?: continue
            if (coords.length() < 2) continue
            val lon = coords.getDouble(0)
            val lat = coords.getDouble(1)

            val name = props.optString("name", "").ifBlank { continue }

            val osmKey   = props.optString("osm_key", "")
            val osmValue = props.optString("osm_value", "")
            val osmKind  = if (osmKey.isNotBlank()) "$osmKey=$osmValue" else null

            val subtitle = listOfNotNull(
                props.optString("street", "").takeIf { it.isNotBlank() },
                props.optString("housenumber", "").takeIf { it.isNotBlank() },
                props.optString("district", "").takeIf { it.isNotBlank() },
                props.optString("city", "").takeIf { it.isNotBlank() },
                props.optString("state", "").takeIf { it.isNotBlank() }
            ).joinToString(" · ")

            // osm_id is only unique within its type: node 42 and way 42 are different objects, and
            // both show up in real result sets. Without the type in the id, the UI's id-keyed
            // dedupe would drop one of them.
            val osmType = props.optString("osm_type", "")
            results += SearchItem(
                id      = "photon_${osmType}${props.optLong("osm_id", i.toLong())}",
                title   = name,
                subtitle = subtitle,
                category = osmCategoryLabel(osmKey, osmValue),
                coordinate = GeoCoordinate(lat, lon),
                source  = SearchSource.ONLINE,
                osmKind = osmKind
            )
        }
        return results
    }

    /**
     * Merges offline presets with online results, deduplicates by coordinate proximity (~30 m)
     * or case-insensitive title, then ranks by text-match quality with distance as a tie-break.
     *
     * Score tiers (higher wins):
     * - 3  exact title prefix  ("Conn" → "Connaught Place")
     * - 2  word-boundary prefix ("maidan" → "Pragati Maidan")
     * - 1  substring anywhere  ("gate" → "India Gate")
     * - 0  no text match       (empty query / nearby)
     */
    private fun mergeAndRank(
        offline: List<SearchItem>,
        online: List<SearchItem>,
        query: String,
        userLat: Double,
        userLon: Double
    ): List<SearchItem> {
        val seenCoord  = mutableSetOf<String>()
        val seenTitle  = mutableSetOf<String>()
        val merged     = mutableListOf<SearchItem>()

        fun coordKey(item: SearchItem): String {
            // 0.0003° ≈ 33 m — two items this close are treated as duplicates
            val lg = (item.coordinate.latitude  / 0.0003).roundToInt()
            val og = (item.coordinate.longitude / 0.0003).roundToInt()
            return "${lg}_$og"
        }

        for (item in offline + online) {
            val ck = coordKey(item)
            val tk = item.title.lowercase().trim()
            // admit if BOTH the coordinate slot AND the title slot are new
            if (seenCoord.add(ck) || seenTitle.add(tk)) {
                seenCoord.add(ck)
                seenTitle.add(tk)
                merged += item
            }
        }

        val q = query.lowercase()
        return merged.sortedWith(
            compareByDescending<SearchItem> { item ->
                if (q.isEmpty()) 0
                else {
                    val t = item.title.lowercase()
                    val s = item.subtitle.lowercase()
                    when {
                        t.startsWith(q)                                     -> 3
                        t.split(' ', '-', ',').any { it.startsWith(q) }    -> 2
                        t.contains(q) || s.contains(q)                     -> 1
                        else                                                -> 0
                    }
                }
            }.thenBy { item ->
                SearchPreset.distanceBetweenM(
                    userLat, userLon,
                    item.coordinate.latitude, item.coordinate.longitude
                )
            }
        )
    }

    private fun osmCategoryLabel(key: String, value: String): String = when {
        key == "amenity" && value == "fuel"                                        -> "Fuel"
        key == "amenity" && value in listOf("restaurant", "cafe", "fast_food")    -> "Food"
        key == "amenity" && value == "parking"                                     -> "Parking"
        key == "amenity" && value == "hospital"                                    -> "Hospital"
        key == "aeroway"                                                            -> "Airports"
        key == "highway" && value == "tunnel"                                       -> "Tunnels"
        else                                                                        -> "Search"
    }

    /** Throttle guard — sleeps until 1 second has elapsed since the last Nominatim call. */
    private fun throttleNominatim() {
        val now   = System.currentTimeMillis()
        val since = now - lastNominatimCallMs
        if (since < 1_000L) Thread.sleep(1_000L - since)
        lastNominatimCallMs = System.currentTimeMillis()
    }

    private val Double.fmt5: String get() = "%.5f".format(this)

    companion object {
        /** Singleton used by the production UI. Tests create their own instance with a fake fetcher. */
        val default: GeocodingService by lazy { GeocodingService() }

        /** How far a category pill with no query text looks, in km (Photon's `radius` unit). */
        const val NEARBY_RADIUS_KM = 5
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Default HTTP fetcher (top-level so tests can reference it by name)
// ────────────────────────────────────────────────────────────────────────────

private const val USER_AGENT        = "IDR-Navigator/1.0 (SIH-26168 Intelligent Dead Reckoning)"
private const val CONNECT_TIMEOUT_MS = 2_500
private const val READ_TIMEOUT_MS    = 3_000

/**
 * Opens an [HttpURLConnection], reads the response body as UTF-8 text, and returns it.
 * Throws [java.io.IOException] on non-200 status or connection failure.
 */
fun defaultFetch(url: String): String {
    val conn = (URL(url).openConnection() as HttpURLConnection).apply {
        requestMethod = "GET"
        setRequestProperty("User-Agent", USER_AGENT)
        connectTimeout = CONNECT_TIMEOUT_MS
        readTimeout    = READ_TIMEOUT_MS
    }
    return try {
        if (conn.responseCode != HttpURLConnection.HTTP_OK) {
            throw java.io.IOException("HTTP ${conn.responseCode} for $url")
        }
        BufferedReader(InputStreamReader(conn.inputStream, "UTF-8")).use { it.readText() }
    } finally {
        conn.disconnect()
    }
}

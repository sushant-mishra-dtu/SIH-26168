package com.sih.idr.demo.backend.routing

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

class GeocodingServiceTest {

    private val userLat = 28.6129
    private val userLon = 77.2295

    @Test
    fun photonParsesCoordinatesAndPropertiesCorrectly() = runBlocking {
        // GeoJSON coordinates are [lon, lat]: index 0 is lon, 1 is lat
        val cannedPhotonJson = """
        {
          "type": "FeatureCollection",
          "features": [
            {
              "type": "Feature",
              "geometry": {
                "type": "Point",
                "coordinates": [77.2090, 28.5355]
              },
              "properties": {
                "osm_id": 123456,
                "osm_key": "amenity",
                "osm_value": "hospital",
                "name": "Max Super Speciality Hospital",
                "countrycode": "in",
                "city": "New Delhi",
                "state": "Delhi"
              }
            }
          ]
        }
        """.trimIndent()

        val service = GeocodingService(
            fetcher = { _ -> cannedPhotonJson },
            presets = emptyList()
        )

        val results = service.search("Max Hospital", userLat, userLon)
        assertEquals(1, results.size)
        val item = results[0]
        assertEquals("Max Super Speciality Hospital", item.title)
        // coordinates must be lat=28.5355, lon=77.2090
        assertEquals(28.5355, item.coordinate.latitude, 0.0001)
        assertEquals(77.2090, item.coordinate.longitude, 0.0001)
        assertEquals(SearchSource.ONLINE, item.source)
        assertEquals("Hospital", item.category)
        assertEquals("amenity=hospital", item.osmKind)
    }

    @Test
    fun photonDropsNonIndiaResults() = runBlocking {
        val mixedJson = """
        {
          "type": "FeatureCollection",
          "features": [
            {
              "type": "Feature",
              "geometry": { "type": "Point", "coordinates": [-0.1278, 51.5074] },
              "properties": {
                "osm_id": 1,
                "name": "London Eye",
                "countrycode": "gb"
              }
            },
            {
              "type": "Feature",
              "geometry": { "type": "Point", "coordinates": [77.2295, 28.6129] },
              "properties": {
                "osm_id": 2,
                "name": "India Gate Delhi",
                "countrycode": "in"
              }
            }
          ]
        }
        """.trimIndent()

        val service = GeocodingService(
            fetcher = { _ -> mixedJson },
            presets = emptyList()
        )

        val results = service.search("gate", userLat, userLon)
        assertEquals(1, results.size)
        assertEquals("India Gate Delhi", results[0].title)
    }

    @Test
    fun nominatimFallbackParsesCorrectlyWhenPhotonEmpty() = runBlocking {
        val cannedNominatimJson = """
        [
          {
            "osm_id": 98765,
            "lat": "28.6328",
            "lon": "77.2197",
            "display_name": "Palika Bazaar, Connaught Place, New Delhi, Delhi, 110001, India"
          }
        ]
        """.trimIndent()

        val service = GeocodingService(
            fetcher = { url ->
                if (url.contains("photon.komoot.io")) {
                    """{"type":"FeatureCollection","features":[]}"""
                } else {
                    cannedNominatimJson
                }
            },
            presets = emptyList()
        )

        val results = service.search("Palika Bazaar", userLat, userLon)
        assertEquals(1, results.size)
        val item = results[0]
        assertEquals("Palika Bazaar", item.title)
        assertTrue(item.subtitle.contains("Connaught Place"))
        assertEquals(28.6328, item.coordinate.latitude, 0.0001)
        assertEquals(77.2197, item.coordinate.longitude, 0.0001)
        assertEquals(SearchSource.ONLINE, item.source)
    }

    @Test
    fun networkFailureReturnsPresetsSilentlyWithoutException() = runBlocking {
        val service = GeocodingService(
            fetcher = { _ -> throw IOException("Network unreachable") },
            presets = SearchPreset.PRESETS
        )

        val results = service.search("Connaught", userLat, userLon)
        assertFalse("Should return presets rather than empty or throw", results.isEmpty())
        assertTrue("Preset Connaught Place should be found", results.any { it.title.contains("Connaught") })
    }

    @Test
    fun rankingPrefersExactTitlePrefix() = runBlocking {
        val itemA = SearchItem(
            id = "a",
            title = "South Connaught Extension",
            subtitle = "Outer Ring",
            category = "Search",
            coordinate = GeoCoordinate(28.6000, 77.2000),
            source = SearchSource.ONLINE
        )
        val itemB = SearchItem(
            id = "b",
            title = "Connaught Place",
            subtitle = "Inner Circle",
            category = "Landmarks",
            coordinate = GeoCoordinate(28.6315, 77.2167),
            source = SearchSource.PRESET
        )

        val service = GeocodingService(
            fetcher = { _ ->
                """
                {
                  "type": "FeatureCollection",
                  "features": [
                    {
                      "type": "Feature",
                      "geometry": { "type": "Point", "coordinates": [77.2000, 28.6000] },
                      "properties": { "osm_id": 99, "name": "South Connaught Extension", "countrycode": "in" }
                    }
                  ]
                }
                """.trimIndent()
            },
            presets = listOf(itemB)
        )

        val results = service.search("conn", userLat, userLon)
        assertTrue(results.size >= 2)
        // "Connaught Place" starts with "conn" -> score 3
        // "South Connaught Extension" has word boundary -> score 2
        assertEquals("Connaught Place", results[0].title)
    }

    @Test
    fun reverseGeocodingParsesPhotonFirst() = runBlocking {
        val cannedReversePhoton = """
        {
          "type": "FeatureCollection",
          "features": [
            {
              "type": "Feature",
              "geometry": { "type": "Point", "coordinates": [77.2295, 28.6129] },
              "properties": {
                "osm_id": 111,
                "name": "Kartavya Path Central",
                "countrycode": "in",
                "city": "New Delhi"
              }
            }
          ]
        }
        """.trimIndent()

        val service = GeocodingService(
            fetcher = { _ -> cannedReversePhoton },
            presets = emptyList()
        )

        val result = service.reverse(28.6129, 77.2295)
        assertNotNull(result)
        assertEquals("Kartavya Path Central", result!!.title)
        assertEquals(SearchSource.PIN, result.source)
    }

    // ── The requests Photon actually gets ────────────────────────────────────
    // Photon's tag filter is `key:value`; the app's pills and osmKind use `key=value`. Sent
    // verbatim, the public instance returns zero features for every filtered search, and its
    // /api endpoint is HTTP 400 without `q`, so a nearby search routed through it is always empty.

    private val emptyCollection = """{"type":"FeatureCollection","features":[]}"""

    @Test
    fun photonTagFilterIsSentAsKeyColonValue() = runBlocking {
        val urls = mutableListOf<String>()
        val service = GeocodingService(
            fetcher = { url -> urls += url; emptyCollection },
            presets = emptyList()
        )
        service.search("petrol", userLat, userLon, osmTagFilter = "amenity=fuel")
        val photon = urls.first { it.startsWith("https://photon.komoot.io/api/") }
        assertTrue(photon, photon.contains("osm_tag=amenity%3Afuel"))
        assertFalse(photon, photon.contains("%3D"))
    }

    @Test
    fun nearbyUsesReverseWithTagAndRadiusNotApiWithoutQuery() = runBlocking {
        val urls = mutableListOf<String>()
        val service = GeocodingService(
            fetcher = { url -> urls += url; emptyCollection },
            presets = emptyList()
        )
        service.nearby(userLat, userLon, "amenity=fuel")
        assertEquals(1, urls.size)
        val url = urls.single()
        assertTrue(url, url.startsWith("https://photon.komoot.io/reverse?"))
        assertTrue(url, url.contains("osm_tag=amenity%3Afuel"))
        assertTrue(url, url.contains("radius=${GeocodingService.NEARBY_RADIUS_KM}"))
        assertFalse(url, url.contains("q="))
    }

    @Test
    fun photonNodeAndWayWithTheSameOsmIdAreDistinctResults() = runBlocking {
        // osm_id is unique per type only. The UI dedupes suggestions by id, so a shared id
        // would silently drop one of two real places.
        val twoObjects = """
        {
          "type": "FeatureCollection",
          "features": [
            {
              "type": "Feature",
              "geometry": { "type": "Point", "coordinates": [77.2245, 28.6045] },
              "properties": { "osm_type": "N", "osm_id": 42, "name": "Jiwan Service Station", "countrycode": "IN" }
            },
            {
              "type": "Feature",
              "geometry": { "type": "Point", "coordinates": [77.2405, 28.6146] },
              "properties": { "osm_type": "W", "osm_id": 42, "name": "Ram Service Station", "countrycode": "IN" }
            }
          ]
        }
        """.trimIndent()
        val service = GeocodingService(fetcher = { _ -> twoObjects }, presets = emptyList())
        val results = service.nearby(userLat, userLon, "amenity=fuel")
        assertEquals(2, results.size)
        assertEquals(2, results.map { it.id }.toSet().size)
        assertTrue(results.any { it.id == "photon_N42" })
        assertTrue(results.any { it.id == "photon_W42" })
    }

    // ── Offline means every geocoder tried threw, not that nothing matched ──

    @Test
    fun searchWithStatusReportsOfflineOnNetworkFailure() = runBlocking {
        val service = GeocodingService(
            fetcher = { _ -> throw IOException("No route to host") },
            presets = SearchPreset.PRESETS
        )

        val result = service.searchWithStatus("Connaught", userLat, userLon)
        assertTrue("isOffline must be true when network throws", result.isOffline)
        assertFalse("Presets should still be returned as fallback", result.items.isEmpty())
    }

    @Test
    fun searchWithStatusReportsOnlineEvenWhenResultsEmpty() = runBlocking {
        // Photon and Nominatim return valid empty responses (device is online, just 0 matches)
        val service = GeocodingService(
            fetcher = { url ->
                if (url.contains("photon.komoot.io")) {
                    """{"type":"FeatureCollection","features":[]}"""
                } else {
                    "[]"
                }
            },
            presets = emptyList()
        )

        val result = service.searchWithStatus("xyznonsensequery123", userLat, userLon)
        assertFalse("isOffline must be false when network succeeds with 0 matches", result.isOffline)
        assertTrue("Result items should be empty", result.items.isEmpty())
    }

    @Test
    fun nearbyWithStatusReportsOfflineOnFailure() = runBlocking {
        val failingService = GeocodingService(
            fetcher = { _ -> throw IOException("DNS resolution failed") }
        )
        val offlineResult = failingService.nearbyWithStatus(userLat, userLon, "amenity=fuel")
        assertTrue("nearbyWithStatus must be offline on network error", offlineResult.isOffline)

        val workingService = GeocodingService(
            fetcher = { _ -> """{"type":"FeatureCollection","features":[]}""" }
        )
        val onlineResult = workingService.nearbyWithStatus(userLat, userLon, "amenity=fuel")
        assertFalse("nearbyWithStatus must not be offline when network succeeds", onlineResult.isOffline)
    }

    @Test
    fun searchWithStatusIsOnlineWhenPhotonAnswersEmptyAndNominatimThrows() = runBlocking {
        // Photon's 200 proves the network is up; a Nominatim failure afterwards is not "offline".
        val service = GeocodingService(
            fetcher = { url ->
                if (url.contains("photon.komoot.io")) emptyCollection
                else throw IOException("nominatim unreachable")
            },
            presets = emptyList()
        )
        val result = service.searchWithStatus("xyznonsensequery123", userLat, userLon)
        assertFalse(result.isOffline)
        assertTrue(result.items.isEmpty())
    }

    @Test
    fun searchWithStatusShortQueryIsOfflineOnlyWhenPhotonThrows() = runBlocking {
        // Under three characters Nominatim is never tried, so Photon alone decides.
        val failing = GeocodingService(fetcher = { _ -> throw IOException("down") }, presets = emptyList())
        assertTrue(failing.searchWithStatus("co", userLat, userLon).isOffline)

        val empty = GeocodingService(fetcher = { _ -> emptyCollection }, presets = emptyList())
        assertFalse(empty.searchWithStatus("co", userLat, userLon).isOffline)
    }
}

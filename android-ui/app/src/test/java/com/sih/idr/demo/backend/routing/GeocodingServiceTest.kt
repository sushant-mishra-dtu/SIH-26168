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
}

package com.sih.idr.demo.backend.routing

import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

/**
 * Persists the last [MAX_RECENTS] selected destinations in [SharedPreferences] as a JSON array.
 *
 * Selecting a destination (search result, preset, or dropped pin) records it here. Re-selecting
 * an existing entry moves it to the top rather than creating a duplicate. Recents are shown in
 * the search bar when the field is focused and empty, above presets, with a clock icon.
 *
 * Storage schema: one string key in the supplied [SharedPreferences] instance. Value is a JSON
 * array of objects with the fields: id, title, subtitle, lat, lon, category, osmKind, timestamp.
 * No Room, no new Gradle dependencies.
 *
 * @param prefs The [SharedPreferences] instance to read from and write to.
 */
class RecentSearches(private val prefs: SharedPreferences) {

    /**
     * Records a selected [item] as a recent search.
     *
     * If the item's [SearchItem.id] already exists in the list it is moved to the front.
     * If the list exceeds [MAX_RECENTS] after insertion the oldest entry is dropped.
     */
    fun record(item: SearchItem) {
        val current = all().toMutableList()
        // Remove any existing entry with the same id so we re-add it at position 0
        current.removeAll { it.id == item.id }
        current.add(0, item)
        // Enforce cap
        val capped = if (current.size > MAX_RECENTS) current.take(MAX_RECENTS) else current
        save(capped)
    }

    /** Returns all stored recent searches, most-recently-selected first. */
    fun all(): List<SearchItem> {
        val raw = prefs.getString(PREF_KEY, null) ?: return emptyList()
        return runCatching { deserialize(raw) }.getOrDefault(emptyList())
    }

    /**
     * Removes the entry with the given [id] from the recent list.
     * A no-op if no such entry exists.
     */
    fun remove(id: String) {
        val updated = all().filter { it.id != id }
        save(updated)
    }

    // ── Serialisation ────────────────────────────────────────────────────────

    private fun save(items: List<SearchItem>) {
        prefs.edit().putString(PREF_KEY, serialize(items)).apply()
    }

    private fun serialize(items: List<SearchItem>): String {
        val array = JSONArray()
        for (item in items) {
            array.put(
                JSONObject().apply {
                    put("id",        item.id)
                    put("title",     item.title)
                    put("subtitle",  item.subtitle)
                    put("lat",       item.coordinate.latitude)
                    put("lon",       item.coordinate.longitude)
                    put("category",  item.category)
                    put("osmKind",   item.osmKind ?: JSONObject.NULL)
                    put("timestamp", System.currentTimeMillis())
                }
            )
        }
        return array.toString()
    }

    private fun deserialize(json: String): List<SearchItem> {
        val array = JSONArray(json)
        val items = mutableListOf<SearchItem>()
        for (i in 0 until array.length()) {
            val obj = array.getJSONObject(i)
            val lat = obj.optDouble("lat", Double.NaN)
            val lon = obj.optDouble("lon", Double.NaN)
            if (lat.isNaN() || lon.isNaN()) continue
            items += SearchItem(
                id         = obj.optString("id", "recent_$i"),
                title      = obj.optString("title", ""),
                subtitle   = obj.optString("subtitle", ""),
                category   = obj.optString("category", "Search"),
                coordinate = GeoCoordinate(lat, lon),
                source     = SearchSource.RECENT,
                osmKind    = obj.optString("osmKind", "").takeIf { it.isNotBlank() }
            )
        }
        return items
    }

    companion object {
        private const val PREF_KEY   = "idr_recent_searches"
        const val MAX_RECENTS        = 10
    }
}

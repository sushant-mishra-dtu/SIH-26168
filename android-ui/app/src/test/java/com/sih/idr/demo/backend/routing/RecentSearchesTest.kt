package com.sih.idr.demo.backend.routing

import android.content.SharedPreferences
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RecentSearchesTest {

    private val fakePrefs = FakeSharedPreferences()
    private val recentSearches = RecentSearches(fakePrefs)

    private fun sampleItem(id: String, title: String) = SearchItem(
        id = id,
        title = title,
        subtitle = "Subtitle for $title",
        category = "Search",
        coordinate = GeoCoordinate(28.6, 77.2),
        source = SearchSource.RECENT
    )

    @Test
    fun recordsItemsMostRecentFirst() {
        val item1 = sampleItem("1", "Place One")
        val item2 = sampleItem("2", "Place Two")

        recentSearches.record(item1)
        recentSearches.record(item2)

        val all = recentSearches.all()
        assertEquals(2, all.size)
        assertEquals("2", all[0].id)
        assertEquals("1", all[1].id)
    }

    @Test
    fun capsAtTenItems() {
        for (i in 1..15) {
            recentSearches.record(sampleItem(i.toString(), "Place $i"))
        }

        val all = recentSearches.all()
        assertEquals(10, all.size)
        // Most recent should be 15, oldest kept should be 6
        assertEquals("15", all.first().id)
        assertEquals("6", all.last().id)
    }

    @Test
    fun reSelectingExistingItemBumpsToTop() {
        recentSearches.record(sampleItem("a", "Place A"))
        recentSearches.record(sampleItem("b", "Place B"))
        recentSearches.record(sampleItem("c", "Place C"))

        // Re-select "a"
        recentSearches.record(sampleItem("a", "Place A"))

        val all = recentSearches.all()
        assertEquals(3, all.size)
        assertEquals("a", all[0].id)
        assertEquals("c", all[1].id)
        assertEquals("b", all[2].id)
    }

    @Test
    fun removeDeletesSpecifiedItem() {
        recentSearches.record(sampleItem("1", "Place One"))
        recentSearches.record(sampleItem("2", "Place Two"))

        recentSearches.remove("1")

        val all = recentSearches.all()
        assertEquals(1, all.size)
        assertEquals("2", all[0].id)
        assertFalse(all.any { it.id == "1" })
    }
}

/**
 * Minimal in-memory FakeSharedPreferences for JVM unit testing without Robolectric or mocks.
 */
private class FakeSharedPreferences : SharedPreferences {
    private val map = mutableMapOf<String, Any?>()

    override fun getAll(): MutableMap<String, *> = map.toMutableMap()
    override fun getString(key: String?, defValue: String?): String? = (map[key] as? String) ?: defValue
    override fun getStringSet(key: String?, defValues: MutableSet<String>?): MutableSet<String>? =
        (map[key] as? MutableSet<String>) ?: defValues
    override fun getInt(key: String?, defValue: Int): Int = (map[key] as? Int) ?: defValue
    override fun getLong(key: String?, defValue: Long): Long = (map[key] as? Long) ?: defValue
    override fun getFloat(key: String?, defValue: Float): Float = (map[key] as? Float) ?: defValue
    override fun getBoolean(key: String?, defValue: Boolean): Boolean = (map[key] as? Boolean) ?: defValue
    override fun contains(key: String?): Boolean = map.containsKey(key)
    override fun edit(): SharedPreferences.Editor = FakeEditor(map)
    override fun registerOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener?) {}
    override fun unregisterOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener?) {}

    private class FakeEditor(private val backingMap: MutableMap<String, Any?>) : SharedPreferences.Editor {
        private val pending = mutableMapOf<String, Any?>()
        private val removes = mutableSetOf<String>()
        private var clear = false

        override fun putString(key: String?, value: String?): SharedPreferences.Editor {
            if (key != null) pending[key] = value
            return this
        }
        override fun putStringSet(key: String?, values: MutableSet<String>?): SharedPreferences.Editor {
            if (key != null) pending[key] = values
            return this
        }
        override fun putInt(key: String?, value: Int): SharedPreferences.Editor {
            if (key != null) pending[key] = value
            return this
        }
        override fun putLong(key: String?, value: Long): SharedPreferences.Editor {
            if (key != null) pending[key] = value
            return this
        }
        override fun putFloat(key: String?, value: Float): SharedPreferences.Editor {
            if (key != null) pending[key] = value
            return this
        }
        override fun putBoolean(key: String?, value: Boolean): SharedPreferences.Editor {
            if (key != null) pending[key] = value
            return this
        }
        override fun remove(key: String?): SharedPreferences.Editor {
            if (key != null) removes.add(key)
            return this
        }
        override fun clear(): SharedPreferences.Editor {
            clear = true
            return this
        }
        override fun commit(): Boolean {
            apply()
            return true
        }
        override fun apply() {
            if (clear) backingMap.clear()
            removes.forEach { backingMap.remove(it) }
            backingMap.putAll(pending)
        }
    }
}

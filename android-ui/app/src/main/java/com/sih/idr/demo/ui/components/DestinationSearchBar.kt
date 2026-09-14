package com.sih.idr.demo.ui.components

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Flight
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.LocalGasStation
import androidx.compose.material.icons.rounded.LocalHospital
import androidx.compose.material.icons.rounded.LocalParking
import androidx.compose.material.icons.rounded.Place
import androidx.compose.material.icons.rounded.PushPin
import androidx.compose.material.icons.rounded.Restaurant
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material.icons.rounded.Sensors
import androidx.compose.material.icons.rounded.WifiOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.routing.GeocodingService
import com.sih.idr.demo.backend.routing.RecentSearches
import com.sih.idr.demo.backend.routing.SearchItem
import com.sih.idr.demo.backend.routing.SearchPreset
import com.sih.idr.demo.backend.routing.SearchSource
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.glassmorphic
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Locale
import kotlin.math.roundToInt

/** Section label shown in the suggestion list. */
private enum class Section { RECENT, NEARBY, RESULTS }

/** Category pill definition: display label + optional OSM tag filter + icon. */
private data class CategoryPill(
    val label: String,
    val display: String,
    val osmTag: String? = null
)

private val CATEGORY_PILLS = listOf(
    CategoryPill("All",       "All"),
    CategoryPill("Tunnels",   "🚇 Tunnels"),
    CategoryPill("Airports",  "✈️ Airports"),
    CategoryPill("Landmarks", "🏢 Landmarks"),
    CategoryPill("Fuel",      "⛽ Fuel",      osmTag = "amenity=fuel"),
    CategoryPill("Food",      "🍽 Food",       osmTag = "amenity=restaurant"),
    CategoryPill("Parking",   "🅿 Parking",    osmTag = "amenity=parking"),
    CategoryPill("Hospitals", "🏥 Hospitals",  osmTag = "amenity=hospital"),
)

/**
 * Google Maps-style destination search bar.
 *
 * Behaviour:
 * - Search fires from the **first character** typed, debounced 300 ms. Previous job is
 *   cancelled on each keystroke (cancellation-safe).
 * - Empty field + focused: Recents (most-recent-first, long-press to remove) then presets
 *   sorted by distance. Section headers: "Recent" | "Nearby" | "Results".
 * - Category pills filter online results via OSM tags. A pill + empty query runs a nearby
 *   POI search ([GeocodingService.nearby]) rather than returning presets only.
 * - Loading indicator in the trailing slot while a coroutine is in flight.
 * - "Offline — showing saved places" banner when the network path failed.
 * - Keyboard Search action selects the first result.
 * - [expanded]/[onExpandedChange] + [BackHandler] contract is unchanged from the previous
 *   version so [NavigationScreen] controls open/closed state and a map tap can close it.
 *
 * @param recentSearches Optional recent-search store. Pass null to disable recents (e.g., tests).
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun DestinationSearchBar(
    userLat: Double,
    userLon: Double,
    onSelectDestination: (SearchItem) -> Unit,
    modifier: Modifier = Modifier,
    expanded: Boolean = false,
    onExpandedChange: (Boolean) -> Unit = {},
    recentSearches: RecentSearches? = null,
) {
    val palette     = LocalIDRPalette.current
    val focusManager = LocalFocusManager.current
    val scope       = rememberCoroutineScope()

    var query            by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf("All") }
    var suggestions      by remember { mutableStateOf<List<SearchItem>>(emptyList()) }
    var searchJob        by remember { mutableStateOf<Job?>(null) }
    var isLoading        by remember { mutableStateOf(false) }
    var isOffline        by remember { mutableStateOf(false) }
    var recents          by remember { mutableStateOf<List<SearchItem>>(emptyList()) }

    // Load recents once on first composition
    LaunchedEffect(Unit) {
        recents = recentSearches?.all() ?: emptyList()
        suggestions = buildOfflineSuggestions(recents, SearchPreset.findPresets("", "All", userLat, userLon))
    }

    // Sync when expanded state is driven from outside (map tap closes search)
    LaunchedEffect(expanded) {
        if (!expanded) focusManager.clearFocus()
    }

    // ── Core search trigger ───────────────────────────────────────────────────
    /**
     * Cancels any running search job and starts a new one. Fires from the first character.
     * 300 ms debounce before the network call — immediate for preset-only path.
     */
    fun refreshSuggestions(newQuery: String, category: String) {
        searchJob?.cancel()
        searchJob = scope.launch {
            val trimmed = newQuery.trim()
            val pill    = CATEGORY_PILLS.first { it.label == category }

            // Show presets / recents immediately (no debounce)
            val immediate = buildOfflineSuggestions(
                recents,
                SearchPreset.findPresets(trimmed, category, userLat, userLon)
            )
            suggestions = immediate
            isLoading   = false
            isOffline   = false

            // Debounce before hitting the network
            delay(300)
            isLoading = true

            val online: List<SearchItem> = if (trimmed.isEmpty() && pill.osmTag != null) {
                // Empty query + category pill → nearby POI search
                runCatching {
                    GeocodingService.default.nearby(userLat, userLon, pill.osmTag)
                }.getOrNull() ?: emptyList()
            } else if (trimmed.isNotEmpty()) {
                runCatching {
                    GeocodingService.default.search(trimmed, userLat, userLon, pill.osmTag)
                }.getOrNull() ?: emptyList()
            } else {
                emptyList()
            }

            isLoading = false

            if (online.isEmpty() && trimmed.isNotEmpty()) {
                isOffline = true
            }

            suggestions = if (online.isNotEmpty()) {
                buildMergedSuggestions(recents, online)
            } else {
                immediate
            }
        }
    }

    fun updateQuery(newQuery: String) {
        query = newQuery
        refreshSuggestions(newQuery, selectedCategory)
    }

    fun dismiss() {
        onExpandedChange(false)
        focusManager.clearFocus()
    }

    fun selectItem(item: SearchItem) {
        recentSearches?.record(item)
        recents = recentSearches?.all() ?: recents
        dismiss()
        onSelectDestination(item)
    }

    // Back gesture closes the list before leaving the app
    BackHandler(enabled = expanded && suggestions.isNotEmpty()) { dismiss() }

    // ── Layout ────────────────────────────────────────────────────────────────
    Column(
        modifier = modifier
            .fillMaxWidth()
            .animateContentSize()
            .glassmorphic(
                shape           = RoundedCornerShape(22.dp),
                backgroundColor = palette.glassSurface,
                borderWidth     = 1.dp,
                borderColor     = palette.glassBorder,
                glowColor       = Color.Transparent,
                glowRadius      = 4.dp
            )
    ) {
        // ── Search Input Row ──────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector     = Icons.Rounded.Search,
                contentDescription = "Search",
                tint            = palette.primary,
                modifier        = Modifier.size(22.dp)
            )
            Spacer(Modifier.width(10.dp))
            Box(modifier = Modifier.weight(1f)) {
                if (query.isEmpty()) {
                    Text(
                        text  = "Where to? Search anywhere in India…",
                        style = MaterialTheme.typography.bodyMedium,
                        color = palette.textSecondary.copy(alpha = 0.8f)
                    )
                }
                BasicTextField(
                    value       = query,
                    onValueChange = {
                        updateQuery(it)
                        onExpandedChange(true)
                    },
                    textStyle   = MaterialTheme.typography.bodyMedium.copy(
                        color      = palette.textPrimary,
                        fontWeight = FontWeight.Medium
                    ),
                    cursorBrush = SolidColor(palette.primary),
                    singleLine  = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(
                        onSearch = {
                            // Keyboard Search action selects the first result
                            suggestions.firstOrNull()?.let { selectItem(it) }
                                ?: focusManager.clearFocus()
                        }
                    ),
                    modifier    = Modifier
                        .fillMaxWidth()
                        .onFocusChanged { if (it.isFocused) onExpandedChange(true) }
                )
            }

            // Trailing slot: loading spinner while in-flight, clear button otherwise
            when {
                isLoading -> CircularProgressIndicator(
                    modifier       = Modifier.size(18.dp),
                    color          = palette.primary,
                    strokeWidth    = 2.dp
                )
                query.isNotEmpty() -> Icon(
                    imageVector     = Icons.Rounded.Close,
                    contentDescription = "Clear search",
                    tint            = palette.textSecondary,
                    modifier        = Modifier
                        .size(20.dp)
                        .clickable { updateQuery(""); dismiss() }
                )
            }
        }

        // ── Offline Banner ────────────────────────────────────────────────────
        AnimatedVisibility(visible = isOffline) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(palette.statusWarn.copy(alpha = 0.12f))
                    .padding(horizontal = 14.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector     = Icons.Rounded.WifiOff,
                    contentDescription = null,
                    tint            = palette.statusWarn,
                    modifier        = Modifier.size(14.dp)
                )
                Text(
                    text  = "Offline — showing saved places",
                    style = MaterialTheme.typography.labelSmall,
                    color = palette.statusWarn
                )
            }
        }

        // ── Category Pills ────────────────────────────────────────────────────
        LazyRow(
            modifier                  = Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp, vertical = 4.dp),
            horizontalArrangement     = Arrangement.spacedBy(6.dp)
        ) {
            items(CATEGORY_PILLS) { pill ->
                val isSelected = selectedCategory == pill.label
                Surface(
                    color    = if (isSelected) palette.primary.copy(alpha = 0.20f) else Color.Transparent,
                    shape    = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .border(
                            width  = 1.dp,
                            color  = if (isSelected) palette.primary.copy(alpha = 0.8f) else palette.glassBorder,
                            shape  = RoundedCornerShape(12.dp)
                        )
                        .clip(RoundedCornerShape(12.dp))
                        .clickable {
                            selectedCategory = pill.label
                            refreshSuggestions(query, pill.label)
                            onExpandedChange(true)
                        }
                ) {
                    Text(
                        text     = pill.display,
                        style    = MaterialTheme.typography.labelSmall.copy(
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
                        ),
                        color    = if (isSelected) palette.primary else palette.textSecondary,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                    )
                }
            }
        }

        // ── Suggestion List ───────────────────────────────────────────────────
        AnimatedVisibility(
            visible = expanded && suggestions.isNotEmpty(),
            enter   = fadeIn(),
            exit    = fadeOut()
        ) {
            // Annotate suggestions with section headers
            val sectioned = annotateSections(suggestions)

            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 300.dp)
                    .padding(top = 4.dp, bottom = 6.dp)
            ) {
                for ((section, items) in sectioned) {
                    // Section header
                    item(key = "header_$section") {
                        Text(
                            text     = when (section) {
                                Section.RECENT  -> "Recent"
                                Section.NEARBY  -> "Nearby"
                                Section.RESULTS -> "Results"
                            },
                            style    = MaterialTheme.typography.labelSmall.copy(
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 0.8.sp
                            ),
                            color    = palette.textSecondary,
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 4.dp)
                        )
                    }

                    itemsIndexed(items, key = { _, it -> it.id }) { index, item ->
                        if (index > 0) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 14.dp)
                                    .height(0.8.dp)
                                    .background(palette.border.copy(alpha = 0.35f))
                            )
                        }

                        val distM = SearchPreset.distanceBetweenM(
                            userLat, userLon,
                            item.coordinate.latitude, item.coordinate.longitude
                        )
                        val formattedDist = if (distM < 1000f) {
                            "${distM.roundToInt()} m"
                        } else {
                            "%.1f km".format(Locale.US, distM / 1000f)
                        }

                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .combinedClickable(
                                    onClick      = { selectItem(item) },
                                    onLongClick  = if (item.source == SearchSource.RECENT) {
                                        {
                                            recentSearches?.remove(item.id)
                                            recents     = recentSearches?.all() ?: recents
                                            suggestions = buildOfflineSuggestions(
                                                recents,
                                                SearchPreset.findPresets(query, selectedCategory, userLat, userLon)
                                            )
                                        }
                                    } else null
                                )
                                .padding(horizontal = 14.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Category icon
                            Box(
                                modifier         = Modifier
                                    .size(32.dp)
                                    .background(
                                        color  = iconBackground(item, palette.primary),
                                        shape  = CircleShape
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector     = categoryIcon(item),
                                    contentDescription = null,
                                    tint            = iconTint(item, palette.primary),
                                    modifier        = Modifier.size(18.dp)
                                )
                            }

                            Spacer(Modifier.width(10.dp))

                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text     = item.title,
                                    style    = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                                    color    = palette.textPrimary,
                                    maxLines = 1
                                )
                                if (item.subtitle.isNotEmpty()) {
                                    Text(
                                        text     = item.subtitle,
                                        style    = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                        color    = palette.textSecondary,
                                        maxLines = 1
                                    )
                                }
                            }

                            Spacer(Modifier.width(8.dp))

                            Text(
                                text  = formattedDist,
                                style = MaterialTheme.typography.labelSmall.copy(
                                    color      = palette.primary,
                                    fontWeight = FontWeight.Bold
                                )
                            )
                        }
                    }
                }
            }
        }
    }
}

// ── Icon helpers ──────────────────────────────────────────────────────────────

private fun categoryIcon(item: SearchItem): ImageVector = when {
    item.source == SearchSource.RECENT                             -> Icons.Rounded.History
    item.source == SearchSource.PIN                               -> Icons.Rounded.PushPin
    item.osmKind?.startsWith("amenity=fuel") == true              -> Icons.Rounded.LocalGasStation
    item.osmKind?.startsWith("amenity=restaurant") == true ||
        item.osmKind?.startsWith("amenity=cafe") == true ||
        item.osmKind?.startsWith("amenity=fast_food") == true     -> Icons.Rounded.Restaurant
    item.osmKind?.startsWith("amenity=parking") == true           -> Icons.Rounded.LocalParking
    item.osmKind?.startsWith("amenity=hospital") == true          -> Icons.Rounded.LocalHospital
    item.isTunnel                                                  -> Icons.Rounded.Sensors
    item.category == "Airports"                                    -> Icons.Rounded.Flight
    else                                                           -> Icons.Rounded.Place
}

private fun iconBackground(item: SearchItem, primary: Color): Color = when {
    item.source == SearchSource.RECENT -> Color(0xFF6B7280).copy(alpha = 0.14f)
    item.isTunnel                       -> Color(0xFFD97706).copy(alpha = 0.18f)
    else                                -> primary.copy(alpha = 0.12f)
}

private fun iconTint(item: SearchItem, primary: Color): Color = when {
    item.source == SearchSource.RECENT -> Color(0xFF6B7280)
    item.isTunnel                       -> Color(0xFFD97706)
    else                                -> primary
}

// ── List construction helpers ─────────────────────────────────────────────────

/**
 * Builds the offline suggestion list: recents at the top, presets below.
 * Used as the immediate (no-network) response.
 */
private fun buildOfflineSuggestions(
    recents: List<SearchItem>,
    presets: List<SearchItem>
): List<SearchItem> {
    val seen = mutableSetOf<String>()
    val result = mutableListOf<SearchItem>()
    for (r in recents) { if (seen.add(r.id)) result += r }
    for (p in presets) { if (seen.add(p.id)) result += p }
    return result
}

/**
 * Builds the final merged suggestion list: recents first, then online results
 * (which already include ranked presets from [GeocodingService.mergeAndRank]).
 */
private fun buildMergedSuggestions(
    recents: List<SearchItem>,
    online: List<SearchItem>
): List<SearchItem> {
    val seen = mutableSetOf<String>()
    val result = mutableListOf<SearchItem>()
    for (r in recents) { if (seen.add(r.id)) result += r }
    for (o in online) { if (seen.add(o.id)) result += o }
    return result
}

/**
 * Groups a flat suggestion list into ordered (Section → items) pairs for section headers.
 */
private fun annotateSections(
    items: List<SearchItem>
): List<Pair<Section, List<SearchItem>>> {
    val recentItems  = items.filter { it.source == SearchSource.RECENT }
    val nearbyItems  = items.filter { it.source == SearchSource.ONLINE }
    val presetItems  = items.filter { it.source == SearchSource.PRESET }

    val sections = mutableListOf<Pair<Section, List<SearchItem>>>()
    if (recentItems.isNotEmpty())  sections += Section.RECENT  to recentItems
    if (nearbyItems.isNotEmpty())  sections += Section.RESULTS to nearbyItems
    if (presetItems.isNotEmpty())  sections += Section.NEARBY  to presetItems
    return sections
}

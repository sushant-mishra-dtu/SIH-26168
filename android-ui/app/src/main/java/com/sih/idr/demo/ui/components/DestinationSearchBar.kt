package com.sih.idr.demo.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.rounded.Place
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material.icons.rounded.Sensors
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.routing.RouteService
import com.sih.idr.demo.backend.routing.SearchItem
import com.sih.idr.demo.backend.routing.SearchPreset
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.glassmorphic
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Locale
import kotlin.math.roundToInt

/**
 * Consumer-grade destination search bar styled after Google Maps and Mappls.
 * Features fast category pills, pre-cached Delhi NCR corridor presets,
 * and live OpenStreetMap Nominatim destination lookup.
 */
@Composable
fun DestinationSearchBar(
    userLat: Double,
    userLon: Double,
    onSelectDestination: (SearchItem) -> Unit,
    modifier: Modifier = Modifier,
    onExpandedChange: (Boolean) -> Unit = {}
) {
    val palette = LocalIDRPalette.current
    val focusManager = LocalFocusManager.current
    val scope = rememberCoroutineScope()

    var query by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf("All") }
    var suggestions by remember { mutableStateOf<List<SearchItem>>(emptyList()) }
    var isExpanded by remember { mutableStateOf(false) }
    var searchJob by remember { mutableStateOf<Job?>(null) }

    // Notify parent of dropdown expansion state
    LaunchedEffect(isExpanded, suggestions.size) {
        onExpandedChange(isExpanded && suggestions.isNotEmpty())
    }

    // Initialise suggestions from presets
    LaunchedEffect(selectedCategory, userLat, userLon) {
        suggestions = SearchPreset.findPresets(query, selectedCategory, userLat, userLon)
    }

    // Trigger debounced search when query changes
    fun updateQuery(newQuery: String) {
        query = newQuery
        searchJob?.cancel()
        searchJob = scope.launch {
            if (newQuery.length >= 3) {
                delay(250) // Debounce network request
                suggestions = RouteService.searchLocations(newQuery, userLat, userLon, selectedCategory)
            } else {
                suggestions = SearchPreset.findPresets(newQuery, selectedCategory, userLat, userLon)
            }
        }
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .animateContentSize()
            .glassmorphic(
                shape = RoundedCornerShape(22.dp),
                backgroundColor = palette.glassSurface,
                borderWidth = 1.dp,
                borderColor = palette.glassBorder,
                glowColor = Color.Transparent,
                glowRadius = 4.dp
            )
    ) {
        // ── Main Search Input Bar ──────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Rounded.Search,
                contentDescription = "Search",
                tint = palette.primary,
                modifier = Modifier.size(22.dp)
            )

            Spacer(Modifier.width(10.dp))

            Box(modifier = Modifier.weight(1f)) {
                if (query.isEmpty()) {
                    Text(
                        text = "Where to? Search Delhi NCR...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = palette.textSecondary.copy(alpha = 0.8f)
                    )
                }

                BasicTextField(
                    value = query,
                    onValueChange = {
                        updateQuery(it)
                        isExpanded = true
                    },
                    textStyle = MaterialTheme.typography.bodyMedium.copy(
                        color = palette.textPrimary,
                        fontWeight = FontWeight.Medium
                    ),
                    cursorBrush = SolidColor(palette.primary),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(
                        onSearch = {
                            focusManager.clearFocus()
                        }
                    ),
                    modifier = Modifier.fillMaxWidth()
                )
            }

            if (query.isNotEmpty()) {
                Icon(
                    imageVector = Icons.Rounded.Close,
                    contentDescription = "Clear search",
                    tint = palette.textSecondary,
                    modifier = Modifier
                        .size(20.dp)
                        .clickable {
                            query = ""
                            updateQuery("")
                            isExpanded = false
                            focusManager.clearFocus()
                        }
                )
            }
        }

        // ── Category Pills Row ────────────────────────────────────
        LazyRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            items(SearchPreset.CATEGORIES) { category ->
                val isSelected = selectedCategory == category
                Surface(
                    color = if (isSelected) palette.primary.copy(alpha = 0.20f) else Color.Transparent,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .border(
                            width = 1.dp,
                            color = if (isSelected) palette.primary.copy(alpha = 0.8f) else palette.glassBorder,
                            shape = RoundedCornerShape(12.dp)
                        )
                        .clip(RoundedCornerShape(12.dp))
                        .clickable {
                            selectedCategory = category
                            suggestions = SearchPreset.findPresets(query, category, userLat, userLon)
                            isExpanded = true
                        }
                ) {
                    val label = when (category) {
                        "Tunnels" -> "🚇 Tunnels"
                        "Airports" -> "✈️ Airports"
                        "Landmarks" -> "🏢 Landmarks"
                        else -> "All"
                    }
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelSmall.copy(
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
                        ),
                        color = if (isSelected) palette.primary else palette.textSecondary,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                    )
                }
            }
        }

        // ── Dropdown Suggestions List ──────────────────────────────
        AnimatedVisibility(
            visible = isExpanded && suggestions.isNotEmpty(),
            enter = fadeIn(),
            exit = fadeOut()
        ) {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 240.dp)
                    .padding(top = 4.dp, bottom = 6.dp)
            ) {
                itemsIndexed(suggestions, key = { _, it -> it.id }) { index, item ->
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
                        userLat,
                        userLon,
                        item.coordinate.latitude,
                        item.coordinate.longitude
                    )
                    val formattedDist = if (distM < 1000f) {
                        "${distM.roundToInt()} m"
                    } else {
                        "%.1f km".format(Locale.US, distM / 1000f)
                    }

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                isExpanded = false
                                focusManager.clearFocus()
                                onSelectDestination(item)
                            }
                            .padding(horizontal = 14.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Category Icon
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .background(
                                    if (item.isTunnel) Color(0xFFD97706).copy(alpha = 0.18f) else palette.primary.copy(alpha = 0.12f),
                                    CircleShape
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            val icon = when {
                                item.isTunnel -> Icons.Rounded.Sensors
                                item.category == "Airports" -> Icons.Rounded.Flight
                                else -> Icons.Rounded.Place
                            }
                            val iconTint = if (item.isTunnel) Color(0xFFD97706) else palette.primary
                            Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(18.dp))
                        }

                        Spacer(Modifier.width(10.dp))

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = item.title,
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                                color = palette.textPrimary,
                                maxLines = 1
                            )
                            if (item.subtitle.isNotEmpty()) {
                                Text(
                                    text = item.subtitle,
                                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                    color = palette.textSecondary,
                                    maxLines = 1
                                )
                            }
                        }

                        Spacer(Modifier.width(8.dp))

                        Text(
                            text = formattedDist,
                            style = MaterialTheme.typography.labelSmall.copy(
                                color = palette.primary,
                                fontWeight = FontWeight.Bold
                            )
                        )
                    }
                }
            }
        }
    }
}

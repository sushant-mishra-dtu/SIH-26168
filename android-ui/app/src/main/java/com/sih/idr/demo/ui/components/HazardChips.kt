package com.sih.idr.demo.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.BrightnessLow
import androidx.compose.material.icons.rounded.GpsOff
import androidx.compose.material.icons.rounded.Highlight
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Speed
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.glassmorphic

/**
 * Ambient light threshold in lux below which the "Low light" hazard chip is raised (R-F).
 * Unmeasured on the team phone; set as a plausible threshold pending D-116 photometer calibration.
 */
const val LOW_LIGHT_THRESHOLD_LUX = 50f

/**
 * Pure function computing active hazard chip labels based strictly on [TelemetryState] (R-B, R-F).
 *
 * Internal so it can be verified directly by unit tests without Compose runtime dependencies.
 * Complete allowed set:
 * - "Headlights"        when tunnelState in {PRE_ARMED_ENTRY, TUNNEL_ACTIVE_IDR}
 * - "Limit <n> km/h"    when tunnelFix?.inside == true && tunnel.postedLimitKmh != null
 * - "GNSS suppressed"   when telemetry.tunnelModeActive
 * - "Forced"            when telemetry.tunnelForced
 * - "Low light"         when ambientLux != null && ambientLux < LOW_LIGHT_THRESHOLD_LUX
 */
internal fun computeActiveHazardChipLabels(telemetry: TelemetryState): List<String> {
    val labels = mutableListOf<String>()

    if (telemetry.tunnelState == TunnelState.PRE_ARMED_ENTRY ||
        telemetry.tunnelState == TunnelState.TUNNEL_ACTIVE_IDR
    ) {
        labels.add("Headlights")
    }

    val fix = telemetry.tunnelFix
    if (fix?.inside == true && fix.tunnel.postedLimitKmh != null) {
        labels.add("Limit ${fix.tunnel.postedLimitKmh} km/h")
    }

    if (telemetry.tunnelModeActive) {
        labels.add("GNSS suppressed")
    }

    if (telemetry.tunnelForced) {
        labels.add("Forced")
    }

    val lux = telemetry.ambientLux
    if (lux != null && lux < LOW_LIGHT_THRESHOLD_LUX) {
        labels.add("Low light")
    }

    return labels
}

/**
 * Contextual hazard chips reflecting live sensor measurements and tunnel geometry (R-F).
 *
 * Chips appear strictly when derived from measured telemetry or declared asset geometry.
 * No speed-breaker, traffic, or road-condition chips are rendered — the OSM flavour has no data
 * source for them, so they do not exist (R-B, R-F).
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun HazardChips(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier
) {
    val showHeadlights = telemetry.tunnelState == TunnelState.PRE_ARMED_ENTRY ||
        telemetry.tunnelState == TunnelState.TUNNEL_ACTIVE_IDR

    val fix = telemetry.tunnelFix
    val limitKmh = if (fix?.inside == true) fix.tunnel.postedLimitKmh else null
    val showLimit = limitKmh != null

    val showGnssSuppressed = telemetry.tunnelModeActive
    val showForced = telemetry.tunnelForced
    val showLowLight = telemetry.ambientLux != null && telemetry.ambientLux < LOW_LIGHT_THRESHOLD_LUX

    FlowRow(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        AnimatedVisibility(visible = showHeadlights, enter = fadeIn(), exit = fadeOut()) {
            HazardChipItem(label = "Headlights", icon = Icons.Rounded.Highlight)
        }
        AnimatedVisibility(visible = showLimit, enter = fadeIn(), exit = fadeOut()) {
            HazardChipItem(label = "Limit $limitKmh km/h", icon = Icons.Rounded.Speed)
        }
        AnimatedVisibility(visible = showGnssSuppressed, enter = fadeIn(), exit = fadeOut()) {
            HazardChipItem(label = "GNSS suppressed", icon = Icons.Rounded.GpsOff)
        }
        AnimatedVisibility(visible = showForced, enter = fadeIn(), exit = fadeOut()) {
            HazardChipItem(label = "Forced", icon = Icons.Rounded.Lock)
        }
        AnimatedVisibility(visible = showLowLight, enter = fadeIn(), exit = fadeOut()) {
            HazardChipItem(label = "Low light", icon = Icons.Rounded.BrightnessLow)
        }
    }
}

@Composable
private fun HazardChipItem(
    label: String,
    icon: ImageVector,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    Box(
        modifier = modifier
            .glassmorphic(
                shape = RoundedCornerShape(14.dp),
                backgroundColor = palette.statusWarn.copy(alpha = 0.18f),
                borderWidth = 1.dp,
                borderColor = palette.statusWarn.copy(alpha = 0.8f),
                glowColor = palette.statusWarn.copy(alpha = 0.25f),
                glowRadius = 4.dp
            )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
            horizontalArrangement = Arrangement.spacedBy(5.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(13.dp),
                tint = palette.statusWarn
            )
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                color = palette.statusWarn
            )
        }
    }
}

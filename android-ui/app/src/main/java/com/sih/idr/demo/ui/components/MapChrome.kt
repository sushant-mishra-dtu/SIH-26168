package com.sih.idr.demo.ui.components

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.MyLocation
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sih.idr.demo.ui.LocalIDRPalette

/**
 * Compose chrome that floats over the map canvas and does not care which map engine is under it.
 * Both flavours (`osm`, `mapbox`) draw these; the engine-specific composable is `MapView` in each
 * flavour's own source set (D-121).
 */
@Composable
fun MapControlButton(
    icon: ImageVector,
    active: Boolean = false,
    contentDescription: String? = null,
    onClick: () -> Unit
) {
    val palette = LocalIDRPalette.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    Surface(
        color = if (active) palette.primary.copy(alpha = 0.2f) else palette.bgPrimary,
        shape = CircleShape,
        modifier = Modifier
            .size(44.dp)
            .scale(if (isPressed) 0.88f else 1f)
            .shadow(6.dp, CircleShape, spotColor = palette.textDim)
            .border(1.dp, if (active) palette.primary else palette.border, CircleShape)
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
            Icon(
                imageVector = icon,
                contentDescription = contentDescription,
                tint = if (active) palette.primary else palette.textPrimary,
                modifier = Modifier.size(22.dp)
            )
        }
    }
}

/** The Google Maps-style "Re-center" pill shown once the user has panned away from the vehicle. */
@Composable
fun RecenterPill(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val palette = LocalIDRPalette.current
    Surface(
        color = palette.bgPrimary,
        shape = RoundedCornerShape(24.dp),
        shadowElevation = 10.dp,
        modifier = modifier
            .border(1.dp, palette.border, RoundedCornerShape(24.dp))
            .clickable(onClick = onClick)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Icon(
                Icons.Rounded.MyLocation,
                contentDescription = "Re-center",
                tint = palette.primary,
                modifier = Modifier.size(20.dp)
            )
            Text(
                text = "Re-center",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                color = palette.textPrimary
            )
        }
    }
}

/**
 * Per-flavour hooks the shared activity calls. Each flavour source set defines `object MapStack`
 * implementing this; `main` only knows the interface.
 */
interface MapStackHooks {
    /** Called once from `MainActivity.onCreate`, before `setContent`. */
    fun onActivityCreated(activity: androidx.activity.ComponentActivity)

    /** One line naming the engine, for the D-081 caption on the telemetry sheet. */
    val engineCaption: String
}

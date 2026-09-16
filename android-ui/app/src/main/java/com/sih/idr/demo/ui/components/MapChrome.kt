package com.sih.idr.demo.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.MyLocation
import androidx.compose.material.icons.rounded.Remove
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.glassmorphic

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
    val scale = if (isPressed) 0.88f else 1f

    val btnBg = if (active) palette.primary.copy(alpha = 0.25f) else palette.glassSurface
    val btnBorder = if (active) palette.primary else palette.glassBorder

    Box(
        modifier = Modifier
            .size(42.dp)
            .scale(scale)
            .glassmorphic(
                shape = CircleShape,
                backgroundColor = btnBg,
                borderWidth = 1.dp,
                borderColor = btnBorder,
                glowColor = Color.Transparent,
                glowRadius = 4.dp
            )
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            tint = if (active) palette.primary else palette.textPrimary,
            modifier = Modifier.size(20.dp)
        )
    }
}

/**
 * Unified vertical glass capsule for zoom controls (+ and −), styled after Apple Maps and Tesla UI.
 * Single sleek 42dp pill with a subtle hairline divider.
 */
@Composable
fun ZoomCapsule(
    onZoomIn: () -> Unit,
    onZoomOut: () -> Unit,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val inInteraction = remember { MutableInteractionSource() }
    val outInteraction = remember { MutableInteractionSource() }
    val inPressed by inInteraction.collectIsPressedAsState()
    val outPressed by outInteraction.collectIsPressedAsState()

    val shape = RoundedCornerShape(21.dp)

    Box(
        modifier = modifier
            .width(42.dp)
            .height(84.dp)
            .glassmorphic(
                shape = shape,
                backgroundColor = palette.glassSurface,
                borderWidth = 1.dp,
                borderColor = palette.glassBorder,
                glowColor = Color.Transparent,
                glowRadius = 4.dp
            )
            .clip(shape)
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Zoom In (+)
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .scale(if (inPressed) 0.88f else 1f)
                    .clickable(
                        interactionSource = inInteraction,
                        indication = null,
                        onClick = onZoomIn
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Rounded.Add,
                    contentDescription = "Zoom In",
                    tint = palette.textPrimary,
                    modifier = Modifier.size(20.dp)
                )
            }

            // Hairline divider
            Box(
                modifier = Modifier
                    .width(26.dp)
                    .height(1.dp)
                    .background(palette.border.copy(alpha = 0.5f))
            )

            // Zoom Out (−)
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .scale(if (outPressed) 0.88f else 1f)
                    .clickable(
                        interactionSource = outInteraction,
                        indication = null,
                        onClick = onZoomOut
                    ),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Rounded.Remove,
                    contentDescription = "Zoom Out",
                    tint = palette.textPrimary,
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}

/** The Google Maps-style "Re-center" pill shown once the user has panned away from the vehicle. */
@Composable
fun RecenterPill(onClick: () -> Unit, modifier: Modifier = Modifier) {
    val palette = LocalIDRPalette.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    Box(
        modifier = modifier
            .scale(if (isPressed) 0.94f else 1f)
            .glassmorphic(
                shape = RoundedCornerShape(22.dp),
                backgroundColor = palette.glassSurface,
                borderWidth = 1.dp,
                borderColor = palette.glassBorder,
                glowColor = Color.Transparent,
                glowRadius = 6.dp
            )
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Icon(
                Icons.Rounded.MyLocation,
                contentDescription = "Re-center",
                tint = palette.primary,
                modifier = Modifier.size(18.dp)
            )
            Text(
                text = "Re-center",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
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

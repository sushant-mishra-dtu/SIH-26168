package com.sih.idr.demo.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.routing.ManeuverType
import com.sih.idr.demo.backend.routing.NavigationRoute
import com.sih.idr.demo.ui.LocalIDRPalette
import java.util.Locale
import kotlin.math.roundToInt

/**
 * Consumer-grade emerald green turn-by-turn guidance banner modeled after Google Maps and Mappls.
 * Renders next maneuver icon, distance countdown, and street corridor target.
 */
@Composable
fun NavigationHeader(
    route: NavigationRoute,
    stepIndex: Int = 0,
    onCancelRoute: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val currentStep = route.steps.getOrNull(stepIndex) ?: route.steps.firstOrNull()

    // Google Maps signature emerald-green navigation banner color
    val emeraldGreen = Color(0xFF15803D)
    val darkEmerald = Color(0xFF064E3B)

    Surface(
        color = emeraldGreen,
        shape = RoundedCornerShape(20.dp),
        modifier = modifier
            .fillMaxWidth()
            .shadow(12.dp, RoundedCornerShape(20.dp), spotColor = darkEmerald)
            .border(1.dp, Color(0xFF22C55E).copy(alpha = 0.5f), RoundedCornerShape(20.dp))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Maneuver Turn Icon
            val maneuverType = currentStep?.maneuverType ?: ManeuverType.STRAIGHT
            val maneuverIcon = when (maneuverType) {
                ManeuverType.TURN_RIGHT -> Icons.Rounded.TurnRight
                ManeuverType.TURN_LEFT -> Icons.Rounded.TurnLeft
                ManeuverType.SLIGHT_RIGHT -> Icons.Rounded.TurnSlightRight
                ManeuverType.SLIGHT_LEFT -> Icons.Rounded.TurnSlightLeft
                ManeuverType.UTURN -> Icons.Rounded.AltRoute
                ManeuverType.TUNNEL_ENTRY -> Icons.Rounded.Sensors
                ManeuverType.TUNNEL_EXIT -> Icons.Rounded.CheckCircle
                ManeuverType.ARRIVE -> Icons.Rounded.Place
                ManeuverType.STRAIGHT -> Icons.Rounded.Straight
            }

            Box(
                modifier = Modifier
                    .size(44.dp)
                    .background(Color.White.copy(alpha = 0.22f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = maneuverIcon,
                    contentDescription = currentStep?.instruction ?: "Maneuver",
                    tint = Color.White,
                    modifier = Modifier.size(28.dp)
                )
            }

            Spacer(Modifier.width(14.dp))

            // Maneuver distance countdown and street instruction
            Column(modifier = Modifier.weight(1f)) {
                val stepDistM = currentStep?.distanceM ?: 0f
                val distanceText = if (stepDistM < 1000f) {
                    "In ${stepDistM.roundToInt()} m"
                } else {
                    "In %.1f km".format(Locale.US, stepDistM / 1000f)
                }

                Text(
                    text = distanceText,
                    style = MaterialTheme.typography.titleLarge.copy(
                        fontWeight = FontWeight.Bold,
                        fontSize = 20.sp
                    ),
                    color = Color.White
                )

                val streetInstruction = currentStep?.streetName ?: currentStep?.instruction ?: route.destinationName
                Text(
                    text = streetInstruction,
                    style = MaterialTheme.typography.bodyMedium.copy(
                        fontWeight = FontWeight.Medium,
                        fontSize = 14.sp
                    ),
                    color = Color.White.copy(alpha = 0.90f),
                    maxLines = 1
                )
            }

            Spacer(Modifier.width(8.dp))

            // Cancel / Exit route button
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(CircleShape)
                    .background(Color.Black.copy(alpha = 0.25f))
                    .clickable(onClick = onCancelRoute),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Rounded.Close,
                    contentDescription = "Cancel Route",
                    tint = Color.White,
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}

package com.sih.idr.demo.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.routing.ManeuverType
import com.sih.idr.demo.backend.routing.NavigationRoute
import java.util.Locale
import kotlin.math.roundToInt

/**
 * Consumer-grade emerald green turn-by-turn guidance banner modeled after Google Maps and Mappls.
 * Renders live countdown distance, animated route progress bar, next maneuver icon,
 * street corridor target, and integrated tunnel state.
 */
@Composable
fun NavigationHeader(
    route: NavigationRoute,
    stepIndex: Int = 0,
    distanceToNextStepM: Float? = null,
    routeProgressFraction: Float = 0f,
    inTunnel: Boolean = false,
    onCancelRoute: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val currentStep = route.steps.getOrNull(stepIndex) ?: route.steps.firstOrNull()

    // Rich emerald gradient for navigation banner
    val emeraldTop = Color(0xFF0F766E)
    val emeraldBottom = Color(0xFF047857)
    val animatedProgress by animateFloatAsState(
        targetValue = routeProgressFraction.coerceIn(0f, 1f),
        animationSpec = spring(stiffness = 300f),
        label = "route_progress"
    )

    Surface(
        shape = RoundedCornerShape(22.dp),
        modifier = modifier
            .fillMaxWidth()
            .shadow(16.dp, RoundedCornerShape(22.dp), spotColor = Color(0xFF064E3B))
            .border(1.2.dp, Color(0xFF34D399).copy(alpha = 0.55f), RoundedCornerShape(22.dp))
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(emeraldTop, emeraldBottom)
                    )
                )
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(start = 16.dp, end = 14.dp, top = 14.dp, bottom = 12.dp),
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
                            .size(46.dp)
                            .background(Color.White.copy(alpha = 0.22f), CircleShape)
                            .border(1.dp, Color.White.copy(alpha = 0.35f), CircleShape),
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
                        val effectiveDistM = distanceToNextStepM ?: currentStep?.distanceM ?: 0f
                        val distanceText = when {
                            effectiveDistM <= 15f -> "Turn now"
                            effectiveDistM < 1000f -> "In ${effectiveDistM.roundToInt()} m"
                            else -> "In %.1f km".format(Locale.US, effectiveDistM / 1000f)
                        }

                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text(
                                text = distanceText,
                                style = MaterialTheme.typography.titleLarge.copy(
                                    fontWeight = FontWeight.ExtraBold,
                                    fontSize = 21.sp
                                ),
                                color = Color.White
                            )

                            if (inTunnel) {
                                Box(
                                    modifier = Modifier
                                        .background(Color(0xFFD97706), RoundedCornerShape(10.dp))
                                        .padding(horizontal = 6.dp, vertical = 2.dp)
                                ) {
                                    Text(
                                        text = "IDR TUNNEL",
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 9.sp
                                        ),
                                        color = Color.White
                                    )
                                }
                            }
                        }

                        val streetInstruction = currentStep?.streetName
                            ?: currentStep?.instruction
                            ?: route.destinationName
                        Text(
                            text = streetInstruction,
                            style = MaterialTheme.typography.bodyMedium.copy(
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 14.sp
                            ),
                            color = Color.White.copy(alpha = 0.92f),
                            maxLines = 1
                        )
                    }

                    Spacer(Modifier.width(8.dp))

                    // Cancel / Exit route button
                    Box(
                        modifier = Modifier
                            .size(34.dp)
                            .clip(CircleShape)
                            .background(Color.Black.copy(alpha = 0.28f))
                            .clickable(onClick = onCancelRoute),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Rounded.Close,
                            contentDescription = "Cancel Route",
                            tint = Color.White,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }

                // ── Route Trip Completion Progress Bar ───────────────────────
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.5.dp)
                        .background(Color.Black.copy(alpha = 0.20f))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(animatedProgress)
                            .fillMaxHeight()
                            .background(Color(0xFF38BDF8))
                    )
                }
            }
        }
    }
}

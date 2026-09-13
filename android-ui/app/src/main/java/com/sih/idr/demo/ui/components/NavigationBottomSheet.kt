package com.sih.idr.demo.ui.components

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.routing.NavigationRoute
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.LocalIsDarkTheme
import kotlin.math.roundToInt

/**
 * Interactive 2-state navigation card modeled after Google Maps and Mappls.
 *
 * State 1 (Collapsed): Bold ETA, remaining distance, arrival clock time, and prominent action button.
 * State 2 (Expanded): Sliding technical drawer with InEKF sensor telemetry, uncertainty, and provenance disclaimer.
 */
@Composable
fun NavigationBottomSheet(
    telemetry: TelemetryState,
    isRecording: Boolean,
    permissionsGranted: Boolean,
    onStartStop: () -> Unit,
    onResetOrigin: () -> Unit,
    provenanceContent: @Composable () -> Unit,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val isDark = LocalIsDarkTheme.current
    var isExpanded by remember { mutableStateOf(false) }

    Surface(
        color = palette.bgSheet,
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        modifier = modifier
            .fillMaxWidth()
            .shadow(16.dp, RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
            .border(1.dp, palette.border, RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 20.dp, vertical = 12.dp)
        ) {
            // ── Drag Handle / Expand Toggle ────────────────────────────
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { isExpanded = !isExpanded }
                    .padding(vertical = 4.dp),
                horizontalArrangement = Arrangement.Center
            ) {
                Box(
                    modifier = Modifier
                        .width(40.dp)
                        .height(4.dp)
                        .background(palette.textDim.copy(alpha = 0.5f), CircleShape)
                )
            }

            // ── Tier 1: Primary Navigation Summary Bar ─────────────────
            val activeRoute = telemetry.activeRoute
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Left Column: ETA & Destination or Active Trip Summary
                Column(modifier = Modifier.weight(1f)) {
                    if (activeRoute != null) {
                        Row(
                            verticalAlignment = Alignment.Bottom,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            // Bold Emerald ETA
                            Text(
                                text = activeRoute.formattedEta,
                                style = MaterialTheme.typography.headlineMedium.copy(
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 26.sp
                                ),
                                color = Color(0xFF10B981)
                            )

                            // Distance and Arrival Time
                            Text(
                                text = "(${activeRoute.formattedDistance} · ${activeRoute.formattedArrivalTime})",
                                style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp),
                                color = palette.textSecondary,
                                modifier = Modifier.padding(bottom = 3.dp)
                            )
                        }

                        Text(
                            text = "via ${activeRoute.destinationName}",
                            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                            color = palette.textPrimary,
                            maxLines = 1
                        )
                    } else {
                        // Free Map Browsing / Active Recording State
                        Row(
                            verticalAlignment = Alignment.Bottom,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text(
                                text = if (telemetry.running) "Navigating" else "Ready",
                                style = MaterialTheme.typography.headlineSmall.copy(
                                    fontWeight = FontWeight.Bold
                                ),
                                color = if (telemetry.running) palette.primary else palette.textPrimary
                            )

                            if (telemetry.totalDistanceM > 0.5f) {
                                Text(
                                    text = "${telemetry.totalDistanceM.roundToInt()} m logged",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = palette.textSecondary,
                                    modifier = Modifier.padding(bottom = 2.dp)
                                )
                            }
                        }

                        Text(
                            text = if (telemetry.running) "IDR dead-reckoning engine active" else "Tap destination or start navigation",
                            style = MaterialTheme.typography.bodySmall,
                            color = palette.textSecondary
                        )
                    }
                }

                Spacer(Modifier.width(12.dp))

                // Action Buttons: Details toggle + Start/Stop
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Diagnostics Drawer Toggle Button
                    IconButton(
                        onClick = { isExpanded = !isExpanded },
                        modifier = Modifier
                            .size(44.dp)
                            .background(palette.bgCard, CircleShape)
                            .border(1.dp, palette.border, CircleShape)
                    ) {
                        Icon(
                            imageVector = if (isExpanded) Icons.Rounded.KeyboardArrowDown else Icons.Rounded.Tune,
                            contentDescription = if (isExpanded) "Collapse diagnostics" else "Expand diagnostics",
                            tint = if (isExpanded) palette.primary else palette.textSecondary,
                            modifier = Modifier.size(20.dp)
                        )
                    }

                    // Start / Stop Button
                    val interactionSource = remember { MutableInteractionSource() }
                    val isPressed by interactionSource.collectIsPressedAsState()
                    val scale by animateFloatAsState(
                        targetValue = if (isPressed) 0.94f else 1f,
                        animationSpec = spring(dampingRatio = 0.6f, stiffness = 400f),
                        label = "btn_scale"
                    )

                    val isStopState = isRecording || activeRoute != null
                    val buttonBg by animateColorAsState(
                        targetValue = if (isStopState) palette.statusError else palette.primary,
                        animationSpec = spring(stiffness = 400f),
                        label = "btn_bg"
                    )

                    Button(
                        onClick = onStartStop,
                        enabled = permissionsGranted,
                        interactionSource = interactionSource,
                        modifier = Modifier
                            .height(48.dp)
                            .scale(scale),
                        shape = RoundedCornerShape(24.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = buttonBg,
                            disabledContainerColor = palette.textDim.copy(alpha = 0.5f)
                        ),
                        elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
                    ) {
                        Text(
                            text = if (isStopState) "Stop" else "Start",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = if (isDark && !isStopState) Color(0xFF0F172A) else Color.White
                        )
                    }
                }
            }

            // ── Tier 2: Expandable Technical Diagnostics Drawer ─────────
            AnimatedVisibility(
                visible = isExpanded,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp)
                ) {
                    HorizontalDivider(color = palette.border.copy(alpha = 0.6f), thickness = 1.dp)

                    Spacer(Modifier.height(12.dp))

                    Text(
                        text = "IDR FILTER TELEMETRY & DIAGNOSTICS",
                        style = MaterialTheme.typography.labelSmall.copy(
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.sp
                        ),
                        color = palette.textSecondary
                    )

                    // 3 Metric Cards (Speed, uncertainty, sats)
                    TelemetryPanel(telemetry = telemetry)

                    // Live Sensor Stream Row
                    if (isRecording) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 2.dp, bottom = 8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                Icon(Icons.Rounded.Sensors, contentDescription = null, modifier = Modifier.size(14.dp), tint = palette.primary)
                                Text(
                                    text = if (telemetry.sampleRateHz > 0f) "${telemetry.sampleRateHz.toInt()} Hz IMU" else "IMU Active",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = palette.textSecondary
                                )
                            }
                            telemetry.cn0Top4DbHz?.let { cn0 ->
                                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Icon(Icons.Rounded.SatelliteAlt, contentDescription = null, modifier = Modifier.size(14.dp), tint = palette.textSecondary)
                                    Text(
                                        text = "${cn0.roundToInt()} dB-Hz",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = palette.textSecondary
                                    )
                                }
                            }
                            telemetry.ambientLux?.let { lux ->
                                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Icon(Icons.Rounded.Lightbulb, contentDescription = null, modifier = Modifier.size(14.dp), tint = palette.textSecondary)
                                    Text(
                                        text = "${lux.roundToInt()} lx",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = palette.textSecondary
                                    )
                                }
                            }
                        }
                    }

                    // Reset / Origin recenter button row
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.End
                    ) {
                        TextButton(
                            onClick = onResetOrigin,
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Icon(Icons.Rounded.Refresh, contentDescription = null, modifier = Modifier.size(16.dp), tint = palette.textSecondary)
                            Spacer(Modifier.width(6.dp))
                            Text(
                                text = "Reset Pose Origin",
                                style = MaterialTheme.typography.labelMedium,
                                color = palette.textSecondary
                            )
                        }
                    }

                    // Provenance content with mandatory disclaimers
                    provenanceContent()
                }
            }
        }
    }
}

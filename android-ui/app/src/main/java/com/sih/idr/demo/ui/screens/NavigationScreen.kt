package com.sih.idr.demo.ui.screens

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
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
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.DirectionsRun
import androidx.compose.material.icons.rounded.GpsFixed
import androidx.compose.material.icons.rounded.Sensors
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sih.idr.demo.backend.NavigationMode
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.ui.IDRColors
import com.sih.idr.demo.ui.components.MapView
import com.sih.idr.demo.ui.components.TelemetryPanel

/**
 * Main screen — full-bleed map with floating UI overlays matching screenshot style.
 */
@Composable
fun NavigationScreen(
    telemetry: TelemetryState,
    isRecording: Boolean,
    onStartStop: () -> Unit,
    permissionsGranted: Boolean,
    onToggleTunnelMode: () -> Unit = {},
    onResetOrigin: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(IDRColors.BgPrimary)
    ) {
        // ── Full-bleed map ──────────────────────────────────────────
        MapView(
            telemetry = telemetry,
            modifier = Modifier.fillMaxSize()
        )

        // ── Floating Top UI ─────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top
        ) {
            // Tunnel Mode Toggle Pill
            TunnelModeTogglePill(
                active = telemetry.tunnelModeActive,
                enabled = isRecording,
                onClick = onToggleTunnelMode
            )

            // Status Pill (GNSS Denied / Coasting vs GNSS Lock)
            AnimatedVisibility(
                visible = isRecording,
                enter = fadeIn() + slideInVertically { -it },
                exit = fadeOut() + slideOutVertically { -it }
            ) {
                val isIns = telemetry.mode == NavigationMode.INS || telemetry.tunnelModeActive
                Surface(
                    color = IDRColors.OverlayBg,
                    shape = RoundedCornerShape(24.dp),
                    modifier = Modifier.shadow(8.dp, RoundedCornerShape(24.dp), spotColor = IDRColors.TextDim)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (isIns) {
                            Icon(Icons.Rounded.Warning, contentDescription = null, modifier = Modifier.size(16.dp), tint = IDRColors.AmberWarn)
                            Text(
                                "INS Coasting (GNSS Denied)",
                                style = MaterialTheme.typography.titleSmall,
                                color = IDRColors.AmberWarn
                            )
                        } else {
                            Icon(Icons.Rounded.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp), tint = IDRColors.GreenOk)
                            Text(
                                "GNSS Lock",
                                style = MaterialTheme.typography.titleSmall,
                                color = IDRColors.GreenOk
                            )
                        }
                    }
                }
            }

            // Right action icons (Recenter / Clear Track)
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                FloatingIconButton(
                    icon = Icons.Rounded.GpsFixed,
                    onClick = onResetOrigin
                )
            }
        }

        // ── Bottom Sheet Area ───────────────────────────────────────
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
        ) {
            Surface(
                color = IDRColors.BgSheet,
                shape = RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp),
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 16.dp
            ) {
                Column(
                    modifier = Modifier
                        .padding(horizontal = 24.dp, vertical = 24.dp)
                        .navigationBarsPadding()
                ) {
                    // Telemetry cards (Speed, estimator sigma, Sats)
                    TelemetryPanel(telemetry = telemetry)

                    // Secondary info row: Live Sensor Rate & Step / Motion counter
                    if (isRecording) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 4.dp, bottom = 6.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                Icon(Icons.Rounded.Sensors, contentDescription = null, modifier = Modifier.size(14.dp), tint = IDRColors.Blue)
                                Text(
                                    text = if (telemetry.sampleRateHz > 0f) "${telemetry.sampleRateHz.toInt()} Hz IMU" else "IMU Active",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = IDRColors.TextSecondary
                                )
                            }
                            if (telemetry.stepCount > 0) {
                                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Icon(Icons.Rounded.DirectionsRun, contentDescription = null, modifier = Modifier.size(14.dp), tint = IDRColors.TextSecondary)
                                    Text(
                                        text = "${telemetry.stepCount} steps",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = IDRColors.TextSecondary
                                    )
                                }
                            }
                        }
                    }

                    // Caption discipline, D-081. It says what produced the numbers above, and it
                    // is here because a screenshot of this sheet travels further than any README.
                    // Do not drop it because it is ugly on a slide.
                    Text(
                        text = if (telemetry.running) {
                            "On-device demo estimator over the phone's own sensors — not the " +
                                "evaluated InEKF, and not a drift figure. The graded numbers come " +
                                "from the offline harness; the 200 Hz FOG configuration is not " +
                                "demonstrated here."
                        } else {
                            "Not recording. No sensor data has been read, so there is nothing to " +
                                "show — this screen displays no stand-in trajectory."
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = IDRColors.TextSecondary,
                        modifier = Modifier.padding(top = 4.dp)
                    )

                    Spacer(Modifier.height(16.dp))

                    // Action bar (Cancel & Generate/Start)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Cancel / Grant Permissions Button
                        AnimatedContent(
                            targetState = !permissionsGranted,
                            label = "permissions_text",
                            transitionSpec = { fadeIn() togetherWith fadeOut() }
                        ) { showPermissions ->
                            Text(
                                text = if (showPermissions) "Permissions" else "Cancel",
                                style = MaterialTheme.typography.titleMedium,
                                color = IDRColors.TextSecondary,
                                modifier = Modifier
                                    .clip(RoundedCornerShape(12.dp))
                                    .clickable { if (!permissionsGranted) onStartStop() }
                                    .padding(horizontal = 20.dp, vertical = 14.dp)
                            )
                        }

                        // Generate / Start Button (Bounce on tap)
                        val interactionSource = remember { MutableInteractionSource() }
                        val isPressed by interactionSource.collectIsPressedAsState()
                        val scale by animateFloatAsState(
                            targetValue = if (isPressed) 0.94f else 1f,
                            animationSpec = spring(dampingRatio = 0.6f, stiffness = 400f),
                            label = "button_scale"
                        )

                        Button(
                            onClick = onStartStop,
                            enabled = permissionsGranted,
                            interactionSource = interactionSource,
                            modifier = Modifier
                                .weight(1f)
                                .height(56.dp)
                                .padding(start = 12.dp)
                                .scale(scale),
                            shape = RoundedCornerShape(28.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isRecording) IDRColors.RedError else IDRColors.Blue,
                                disabledContainerColor = IDRColors.TextDim.copy(alpha = 0.5f)
                            ),
                            elevation = ButtonDefaults.buttonElevation(defaultElevation = if (permissionsGranted) 4.dp else 0.dp)
                        ) {
                            AnimatedContent(
                                targetState = isRecording,
                                label = "start_stop_text",
                                transitionSpec = {
                                    (slideInVertically { height -> height } + fadeIn())
                                        .togetherWith(slideOutVertically { height -> -height } + fadeOut())
                                }
                            ) { recording ->
                                Text(
                                    if (recording) "Stop" else "Start",
                                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                                    color = IDRColors.BgPrimary
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TunnelModeTogglePill(
    active: Boolean,
    enabled: Boolean,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed && enabled) 0.92f else 1f,
        animationSpec = spring(dampingRatio = 0.6f, stiffness = 400f),
        label = "pill_scale"
    )

    Surface(
        color = if (active) IDRColors.AmberWarn.copy(alpha = 0.18f) else IDRColors.BgPrimary,
        shape = RoundedCornerShape(24.dp),
        modifier = Modifier
            .scale(scale)
            .shadow(8.dp, RoundedCornerShape(24.dp), spotColor = IDRColors.TextDim)
            .then(
                if (active) Modifier.border(1.5.dp, IDRColors.AmberWarn, RoundedCornerShape(24.dp))
                else Modifier
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                enabled = enabled,
                onClick = onClick
            )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = if (active) "Tunnel: ON" else "Tunnel: OFF",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = if (active) IDRColors.AmberWarn else IDRColors.TextPrimary
            )
        }
    }
}

@Composable
private fun FloatingIconButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit = {}
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed) 0.85f else 1f,
        animationSpec = spring(dampingRatio = 0.5f, stiffness = 400f),
        label = "icon_scale"
    )

    Surface(
        color = IDRColors.BgPrimary,
        shape = CircleShape,
        modifier = Modifier
            .size(48.dp)
            .scale(scale)
            .shadow(if (isPressed) 2.dp else 8.dp, CircleShape, spotColor = IDRColors.TextDim)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            )
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = IDRColors.TextPrimary,
                modifier = Modifier.size(24.dp)
            )
        }
    }
}

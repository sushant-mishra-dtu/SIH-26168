package com.sih.idr.demo.ui.screens

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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
import androidx.compose.material.icons.rounded.DarkMode
import androidx.compose.material.icons.rounded.DirectionsRun
import androidx.compose.material.icons.rounded.GpsFixed
import androidx.compose.material.icons.rounded.LightMode
import androidx.compose.material.icons.rounded.Navigation
import androidx.compose.material.icons.rounded.NearMe
import androidx.compose.material.icons.rounded.Route
import androidx.compose.material.icons.rounded.Sensors
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.NavigationMode
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.ui.IDRColors
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.LocalIsDarkTheme
import com.sih.idr.demo.ui.components.MapStack
import com.sih.idr.demo.ui.components.MapView
import com.sih.idr.demo.ui.components.TelemetryPanel
import kotlin.math.roundToInt

/**
 * Main screen — Google Maps-style navigation UI with full-bleed map, turn guidance banner,
 * theme toggle, Course-Up/North-Up switching, and real-time dead-reckoning telemetry.
 */
@Composable
fun NavigationScreen(
    telemetry: TelemetryState,
    isRecording: Boolean,
    onStartStop: () -> Unit,
    permissionsGranted: Boolean,
    onToggleTunnelMode: () -> Unit = {},
    onResetOrigin: () -> Unit = {},
    darkTheme: Boolean = false,
    onToggleTheme: () -> Unit = {},
    courseUpMode: Boolean = false,
    onToggleCourseUp: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val isDark = LocalIsDarkTheme.current
    val isIns = telemetry.mode == NavigationMode.INS || telemetry.tunnelModeActive

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(palette.bgPrimary)
    ) {
        // ── Full-bleed map ──────────────────────────────────────────
        MapView(
            telemetry = telemetry,
            courseUpMode = courseUpMode,
            onToggleCourseUp = onToggleCourseUp,
            modifier = Modifier.fillMaxSize()
        )

        // ── Top Navigation Area (Google Maps Style) ─────────────────
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // 1. Google Maps Navigation Guidance Card
            Surface(
                color = if (isDark) Color(0xFF064E3B) else Color(0xFF0F9D58),
                shape = RoundedCornerShape(20.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .shadow(10.dp, RoundedCornerShape(20.dp), spotColor = Color.Black.copy(alpha = 0.35f))
                    .border(1.dp, Color.White.copy(alpha = 0.2f), RoundedCornerShape(20.dp))
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(14.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        // Direction indicator icon
                        val headingDeg = Math.toDegrees(telemetry.yawRad.toDouble()).toFloat()
                        val targetAngle = if (courseUpMode) -45f else (headingDeg - 45f)
                        val animatedHeading by animateFloatAsState(
                            targetValue = targetAngle,
                            animationSpec = spring(stiffness = 300f),
                            label = "heading_rot"
                        )
                        Surface(
                            color = Color.White.copy(alpha = 0.25f),
                            shape = CircleShape,
                            modifier = Modifier.size(44.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Rounded.NearMe,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier
                                        .size(26.dp)
                                        .rotate(animatedHeading)
                                )
                            }
                        }

                        // Guidance and heading text
                        Column {
                            Text(
                                text = if (telemetry.running) headingToDirection(telemetry.yawRad) else "IDR Navigator",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = Color.White
                            )
                            Spacer(Modifier.height(2.dp))
                            Text(
                                text = if (telemetry.running) {
                                    val distKm = telemetry.totalDistanceM / 1000f
                                    val durSec = telemetry.tripDurationSec
                                    val timeStr = if (durSec >= 60) "${durSec / 60}m ${durSec % 60}s" else "${durSec}s"
                                    "%.2f km traveled • $timeStr".format(distKm)
                                } else {
                                    "Ready to navigate • Tap Start"
                                },
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp),
                                color = Color.White.copy(alpha = 0.85f)
                            )
                        }
                    }

                    // Status Pill (GNSS Lock vs INS Coasting)
                    Surface(
                        color = if (isIns) Color(0x33F59E0B) else Color(0x3310B981),
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.border(
                            1.dp,
                            if (isIns) Color(0xFFFBBF24) else Color(0xFF34D399),
                            RoundedCornerShape(14.dp)
                        )
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            if (isIns) {
                                Icon(
                                    Icons.Rounded.Warning,
                                    contentDescription = null,
                                    modifier = Modifier.size(13.dp),
                                    tint = Color(0xFFFBBF24)
                                )
                                Text(
                                    "INS Coast",
                                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                    color = Color(0xFFFDE68A)
                                )
                            } else {
                                Icon(
                                    Icons.Rounded.CheckCircle,
                                    contentDescription = null,
                                    modifier = Modifier.size(13.dp),
                                    tint = Color(0xFF34D399)
                                )
                                Text(
                                    "GNSS Lock",
                                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                    color = Color(0xFFD1FAE5)
                                )
                            }
                        }
                    }
                }
            }

            // 2. Secondary Floating Bar (Tunnel toggle + Course-Up + Theme Switcher + Recenter)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Tunnel Mode Simulation Toggle Pill
                TunnelModeTogglePill(
                    active = telemetry.tunnelModeActive,
                    enabled = isRecording,
                    onClick = onToggleTunnelMode
                )

                // Quick Action Buttons
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    // Course-Up / North-Up Toggle Button
                    FloatingActionPill(
                        icon = Icons.Rounded.Navigation,
                        active = courseUpMode,
                        contentDescription = if (courseUpMode) "Switch to North-Up" else "Switch to Course-Up",
                        onClick = onToggleCourseUp
                    )

                    // Dark Mode / Light Mode Toggle Button
                    FloatingActionPill(
                        icon = if (isDark) Icons.Rounded.LightMode else Icons.Rounded.DarkMode,
                        contentDescription = "Toggle Dark Mode",
                        onClick = onToggleTheme
                    )

                    // Reset Origin Button
                    FloatingActionPill(
                        icon = Icons.Rounded.GpsFixed,
                        contentDescription = "Reset Origin",
                        onClick = onResetOrigin
                    )
                }
            }
        }

        // ── Bottom Sheet Area ───────────────────────────────────────
        Column(
            modifier = Modifier.align(Alignment.BottomCenter)
        ) {
            Surface(
                color = palette.bgSheet,
                shape = RoundedCornerShape(topStart = 32.dp, topEnd = 32.dp),
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 16.dp,
                border = androidx.compose.foundation.BorderStroke(1.dp, palette.border)
            ) {
                Column(
                    modifier = Modifier
                        .padding(horizontal = 24.dp, vertical = 20.dp)
                        .navigationBarsPadding()
                ) {
                    // Telemetry cards (Speed, estimator sigma, Sats)
                    TelemetryPanel(telemetry = telemetry)

                    // Secondary info row: Live Sensor Rate & Step / Motion counter & Odometry
                    if (isRecording) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 4.dp, bottom = 6.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                Icon(Icons.Rounded.Sensors, contentDescription = null, modifier = Modifier.size(14.dp), tint = palette.primary)
                                Text(
                                    text = if (telemetry.sampleRateHz > 0f) "${telemetry.sampleRateHz.toInt()} Hz IMU" else "IMU Active",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = palette.textSecondary
                                )
                            }
                            if (telemetry.stepCount > 0) {
                                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Icon(Icons.Rounded.DirectionsRun, contentDescription = null, modifier = Modifier.size(14.dp), tint = palette.textSecondary)
                                    Text(
                                        text = "${telemetry.stepCount} steps",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = palette.textSecondary
                                    )
                                }
                            }
                            if (telemetry.totalDistanceM > 0.5f) {
                                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Icon(Icons.Rounded.Route, contentDescription = null, modifier = Modifier.size(14.dp), tint = palette.navGreen)
                                    Text(
                                        text = "${telemetry.totalDistanceM.roundToInt()} m",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = palette.textSecondary
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
                                "demonstrated here. Map: ${MapStack.engineCaption}."
                        } else {
                            "Not recording. No sensor data has been read, so there is nothing to " +
                                "show — this screen displays no stand-in trajectory."
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = palette.textSecondary,
                        modifier = Modifier.padding(top = 4.dp)
                    )

                    Spacer(Modifier.height(16.dp))

                    // Action bar (Reset & Start/Stop)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Reset / Permissions Button
                        AnimatedContent(
                            targetState = !permissionsGranted,
                            label = "permissions_text",
                            transitionSpec = { fadeIn() togetherWith fadeOut() }
                        ) { showPermissions ->
                            Text(
                                text = if (showPermissions) "Permissions" else "Reset",
                                style = MaterialTheme.typography.titleMedium,
                                color = palette.textSecondary,
                                modifier = Modifier
                                    .clip(RoundedCornerShape(12.dp))
                                    .clickable {
                                        if (!permissionsGranted) {
                                            onStartStop()
                                        } else {
                                            onResetOrigin()
                                        }
                                    }
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

                        val buttonBg by animateColorAsState(
                            targetValue = if (isRecording) palette.statusError else palette.primary,
                            animationSpec = spring(stiffness = 400f),
                            label = "btn_bg"
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
                                containerColor = buttonBg,
                                disabledContainerColor = palette.textDim.copy(alpha = 0.5f)
                            ),
                            elevation = ButtonDefaults.buttonElevation(defaultElevation = if (permissionsGranted) 4.dp else 0.dp)
                        ) {
                            AnimatedContent(
                                targetState = isRecording,
                                label = "start_stop_text",
                                transitionSpec = {
                                    fadeIn(animationSpec = spring(stiffness = 500f)) togetherWith
                                        fadeOut(animationSpec = spring(stiffness = 500f))
                                }
                            ) { recording ->
                                Text(
                                    text = if (recording) "Stop" else "Start",
                                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                                    color = if (isDark && !recording) Color(0xFF0F172A) else Color.White
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun headingToDirection(yawRad: Float): String {
    val deg = Math.toDegrees(yawRad.toDouble()).let { (it % 360 + 360) % 360 }
    val directions = arrayOf("North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West")
    val index = (((deg + 22.5) / 45).toInt()) % 8
    return "Heading ${directions[index]} (${deg.roundToInt()}°)"
}

@Composable
private fun TunnelModeTogglePill(
    active: Boolean,
    enabled: Boolean,
    onClick: () -> Unit
) {
    val palette = LocalIDRPalette.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed && enabled) 0.92f else 1f,
        animationSpec = spring(dampingRatio = 0.6f, stiffness = 400f),
        label = "pill_scale"
    )

    Surface(
        color = if (active) palette.statusWarn.copy(alpha = 0.18f) else palette.bgPrimary,
        shape = RoundedCornerShape(24.dp),
        modifier = Modifier
            .scale(scale)
            .shadow(6.dp, RoundedCornerShape(24.dp), spotColor = palette.textDim)
            .border(
                1.dp,
                if (active) palette.statusWarn else palette.border,
                RoundedCornerShape(24.dp)
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                enabled = enabled,
                onClick = onClick
            )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = if (active) "Tunnel: ON" else "Tunnel: OFF",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                color = if (active) palette.statusWarn else palette.textPrimary
            )
        }
    }
}

@Composable
private fun FloatingActionPill(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    active: Boolean = false,
    contentDescription: String? = null,
    onClick: () -> Unit = {}
) {
    val palette = LocalIDRPalette.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed) 0.88f else 1f,
        animationSpec = spring(dampingRatio = 0.5f, stiffness = 400f),
        label = "icon_scale"
    )

    Surface(
        color = if (active) palette.primary.copy(alpha = 0.2f) else palette.bgPrimary,
        shape = CircleShape,
        modifier = Modifier
            .size(40.dp)
            .scale(scale)
            .shadow(6.dp, CircleShape, spotColor = palette.textDim)
            .border(1.dp, if (active) palette.primary else palette.border, CircleShape)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            )
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
            Icon(
                imageVector = icon,
                contentDescription = contentDescription,
                tint = if (active) palette.primary else palette.textPrimary,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

package com.sih.idr.demo.ui.screens

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
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
import androidx.compose.material.icons.rounded.Lightbulb
import androidx.compose.material.icons.rounded.Navigation
import androidx.compose.material.icons.rounded.NearMe
import androidx.compose.material.icons.rounded.Route
import androidx.compose.material.icons.rounded.SatelliteAlt
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
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.launch
import com.sih.idr.demo.backend.NavigationMode
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.TelemetryStore
import com.sih.idr.demo.backend.routing.GeoCoordinate
import com.sih.idr.demo.backend.routing.RouteService
import com.sih.idr.demo.backend.routing.SearchItem
import com.sih.idr.demo.backend.tunnel.TunnelOverride
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.ui.IDRColors
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.LocalIsDarkTheme
import com.sih.idr.demo.ui.components.DestinationSearchBar
import com.sih.idr.demo.ui.components.ExitProgressBar
import com.sih.idr.demo.ui.components.GuidanceBanner
import com.sih.idr.demo.ui.components.HazardChips
import com.sih.idr.demo.ui.components.MapStack
import com.sih.idr.demo.ui.components.MapView
import com.sih.idr.demo.ui.components.NavigationBottomSheet
import com.sih.idr.demo.ui.components.NavigationHeader
import com.sih.idr.demo.ui.components.ReconvergenceToast
import com.sih.idr.demo.ui.components.SpeedHud
import com.sih.idr.demo.ui.components.TelemetryPanel
import com.sih.idr.demo.ui.components.TunnelCorridor
import com.sih.idr.demo.ui.components.TunnelStatusBadge
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
    onSetTunnelOverride: (TunnelOverride) -> Unit = {},
    onResetOrigin: () -> Unit = {},
    darkTheme: Boolean = false,
    onToggleTheme: () -> Unit = {},
    courseUpMode: Boolean = false,
    onToggleCourseUp: () -> Unit = {},
    modifier: Modifier = Modifier
) {    val palette = LocalIDRPalette.current
    val isDark = LocalIsDarkTheme.current
    val scope = rememberCoroutineScope()
    // The status pill follows the tunnel machine (D-126): anything but a healthy lock is amber,
    // and the label is the machine's own state name so a screenshot says which one it was.
    val tunnelState = telemetry.tunnelState
    val isIns = telemetry.mode == NavigationMode.INS || tunnelState != TunnelState.GNSS_HEALTHY

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(palette.bgPrimary)
    ) {
        // ── Full-bleed map (D-121, D-126) ──────────────────────────
        MapView(
            telemetry = telemetry,
            courseUpMode = courseUpMode,
            onToggleCourseUp = onToggleCourseUp,
            modifier = Modifier.fillMaxSize()
        )

        // ── Top Navigation Area (Google Maps & Mappls Style) ────────
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // 1. Destination Search Bar or Active Maneuver Guidance Header
            val activeRoute = telemetry.activeRoute
            if (activeRoute != null) {
                NavigationHeader(
                    route = activeRoute,
                    stepIndex = telemetry.activeStepIndex,
                    onCancelRoute = {
                        TelemetryStore.clearActiveRoute()
                    }
                )
            } else {
                DestinationSearchBar(
                    userLat = telemetry.latitude,
                    userLon = telemetry.longitude,
                    onSelectDestination = { item ->
                        scope.launch {
                            val start = GeoCoordinate(telemetry.latitude, telemetry.longitude)
                            val route = RouteService.fetchRoute(start, item)
                            TelemetryStore.setActiveRoute(route)
                        }
                    }
                )
            }

            // 2. Non-intrusive floating GPS-denied tunnel status badge (D-126)
            TunnelStatusBadge(telemetry = telemetry)

            // 3. State-driven tunnel guidance banner and exit progress bar (D-126)
            GuidanceBanner(
                telemetry = telemetry,
                courseUpMode = courseUpMode
            )

            AnimatedVisibility(
                visible = telemetry.tunnelState == TunnelState.TUNNEL_ACTIVE_IDR && telemetry.tunnelFix?.inside == true,
                enter = fadeIn(),
                exit = fadeOut()
            ) {
                telemetry.tunnelFix?.let { fix ->
                    ExitProgressBar(
                        fix = fix,
                        speedMps = telemetry.speedMps
                    )
                }
            }

            // 4. Contextual hazard chips directly under ExitProgressBar (R-F)
            HazardChips(
                telemetry = telemetry,
                modifier = Modifier.fillMaxWidth()
            )

            // Stage 5: the measured exit summary, for a few seconds after GNSS is back (D-124).
            ReconvergenceToast(summary = telemetry.lastExit)

            // 5. Secondary Floating Bar (Tunnel toggle + Course-Up + Theme Switcher + Recenter)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // 3-way tunnel options selector (D-126): Auto (autonomous FSM), On (force tunnel IDR),
                // Off (force GNSS healthy / suppress tunnel mode)
                TunnelOptionsSelector(
                    currentOverride = telemetry.tunnelOverride,
                    enabled = isRecording,
                    onSelect = onSetTunnelOverride
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

        // ── Bottom Sheet Area & Speed HUD ───────────────────────────
        Column(
            modifier = Modifier.align(Alignment.BottomCenter)
        ) {
            // Speed HUD placed bottom-left directly above the bottom sheet (D-081)
            val postedLimit = if (telemetry.tunnelFix?.inside == true) {
                telemetry.tunnelFix.tunnel.postedLimitKmh
            } else {
                null
            }
            SpeedHud(
                speedMps = telemetry.speedMps,
                postedLimitKmh = postedLimit,
                modifier = Modifier
                    .padding(start = 16.dp, bottom = 8.dp)
                    .align(Alignment.Start)
            )

            NavigationBottomSheet(
                telemetry = telemetry,
                isRecording = isRecording,
                permissionsGranted = permissionsGranted,
                onStartStop = {
                    if (telemetry.activeRoute != null && isRecording) {
                        TelemetryStore.clearActiveRoute()
                    }
                    onStartStop()
                },
                onResetOrigin = onResetOrigin,
                provenanceContent = {
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
                }
            )
        }
    }
}



@Composable
private fun TunnelOptionsSelector(
    currentOverride: TunnelOverride,
    enabled: Boolean,
    onSelect: (TunnelOverride) -> Unit,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current

    Surface(
        color = palette.bgPrimary,
        shape = RoundedCornerShape(20.dp),
        modifier = modifier
            .shadow(6.dp, RoundedCornerShape(20.dp), spotColor = palette.textDim)
            .border(1.dp, palette.border, RoundedCornerShape(20.dp))
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(
                text = "Tunnel",
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                color = palette.textSecondary,
                modifier = Modifier.padding(start = 4.dp, end = 2.dp)
            )

            TunnelOptionSegment(
                label = "Auto",
                selected = currentOverride == TunnelOverride.AUTO,
                activeColor = palette.primary,
                enabled = enabled,
                onClick = { onSelect(TunnelOverride.AUTO) }
            )

            TunnelOptionSegment(
                label = "On",
                selected = currentOverride == TunnelOverride.FORCE_ON,
                activeColor = palette.statusWarn,
                enabled = enabled,
                onClick = { onSelect(TunnelOverride.FORCE_ON) }
            )

            TunnelOptionSegment(
                label = "Off",
                selected = currentOverride == TunnelOverride.FORCE_OFF,
                activeColor = Color(0xFFEF5350),
                enabled = enabled,
                onClick = { onSelect(TunnelOverride.FORCE_OFF) }
            )
        }
    }
}

@Composable
private fun TunnelOptionSegment(
    label: String,
    selected: Boolean,
    activeColor: Color,
    enabled: Boolean,
    onClick: () -> Unit
) {
    val palette = LocalIDRPalette.current
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()
    val scale by animateFloatAsState(
        targetValue = if (isPressed && enabled) 0.90f else 1f,
        animationSpec = spring(dampingRatio = 0.6f, stiffness = 400f),
        label = "segment_scale_$label"
    )

    val bgColor by animateColorAsState(
        targetValue = if (selected) activeColor.copy(alpha = 0.18f) else Color.Transparent,
        animationSpec = spring(dampingRatio = 0.8f, stiffness = 300f),
        label = "segment_bg_$label"
    )
    val borderColor by animateColorAsState(
        targetValue = if (selected) activeColor.copy(alpha = 0.85f) else Color.Transparent,
        animationSpec = spring(dampingRatio = 0.8f, stiffness = 300f),
        label = "segment_border_$label"
    )
    val textColor by animateColorAsState(
        targetValue = if (selected) activeColor else palette.textSecondary,
        animationSpec = spring(dampingRatio = 0.8f, stiffness = 300f),
        label = "segment_text_$label"
    )

    Surface(
        color = bgColor,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .scale(scale)
            .border(1.dp, borderColor, RoundedCornerShape(12.dp))
            .clip(RoundedCornerShape(12.dp))
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                enabled = enabled,
                onClick = onClick
            )
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp)
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall.copy(
                    fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.Medium
                ),
                color = textColor
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

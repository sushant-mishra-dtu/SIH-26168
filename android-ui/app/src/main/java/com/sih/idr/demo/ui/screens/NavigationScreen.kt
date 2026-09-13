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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
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
import com.sih.idr.demo.ui.glassmorphic
import com.sih.idr.demo.ui.components.ArrivalCard
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
) {
    val palette = LocalIDRPalette.current
    val isDark = LocalIsDarkTheme.current
    val scope = rememberCoroutineScope()
    val tunnelState = telemetry.tunnelState
    val inTunnel = tunnelState == TunnelState.TUNNEL_ACTIVE_IDR || telemetry.tunnelModeActive
    val activeRoute = telemetry.activeRoute
    var isSearchExpanded by remember { mutableStateOf(false) }

    val quickActionsAlpha by animateFloatAsState(
        targetValue = if (isSearchExpanded) 0.15f else 1f,
        animationSpec = spring(stiffness = 300f),
        label = "quick_actions_alpha"
    )

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(palette.bgPrimary)
    ) {
        // ── 1. Full-bleed map (D-121, D-126) ──────────────────────────
        MapView(
            telemetry = telemetry,
            courseUpMode = courseUpMode,
            onToggleCourseUp = onToggleCourseUp,
            modifier = Modifier.fillMaxSize()
        )

        // ── 2. Top Navigation Guidance / Search Area ───────────────────
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // A. Active Turn-by-Turn Navigation Header
            if (activeRoute != null) {
                NavigationHeader(
                    route = activeRoute,
                    stepIndex = telemetry.activeStepIndex,
                    distanceToNextStepM = telemetry.distanceToNextStepM,
                    routeProgressFraction = telemetry.routeProgressFraction,
                    inTunnel = inTunnel,
                    onCancelRoute = {
                        TelemetryStore.clearActiveRoute()
                    }
                )

                // Exit progress bar inside tunnel
                AnimatedVisibility(
                    visible = tunnelState == TunnelState.TUNNEL_ACTIVE_IDR && telemetry.tunnelFix?.inside == true,
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

                // Contextual Hazard Chips
                HazardChips(
                    telemetry = telemetry,
                    modifier = Modifier.fillMaxWidth()
                )
            } else {
                // B. Idle Mode: Clean floating search bar
                DestinationSearchBar(
                    userLat = telemetry.latitude,
                    userLon = telemetry.longitude,
                    onExpandedChange = { isSearchExpanded = it },
                    onSelectDestination = { item ->
                        scope.launch {
                            val start = GeoCoordinate(telemetry.latitude, telemetry.longitude)
                            val route = RouteService.fetchRoute(start, item)
                            TelemetryStore.setActiveRoute(route)
                        }
                    }
                )

                // Floating tunnel status badge only when GPS-denied
                TunnelStatusBadge(telemetry = telemetry)

                // Tunnel guidance banner only when tunnel FSM is active and without active route
                if (tunnelState != TunnelState.GNSS_HEALTHY) {
                    GuidanceBanner(
                        telemetry = telemetry,
                        courseUpMode = courseUpMode
                    )
                }
            }

            // Stage 5: Measured exit summary toast after GNSS returns (D-124)
            ReconvergenceToast(summary = telemetry.lastExit)

            // ── 3. Floating Quick Action Controls (Right-side column) ──────
            // Flow naturally below whichever top cards / banners are visible so they never overlap
            AnimatedVisibility(
                visible = !isSearchExpanded,
                enter = fadeIn(),
                exit = fadeOut(),
                modifier = Modifier.align(Alignment.End)
            ) {
                Column(
                    modifier = Modifier.graphicsLayer {
                        alpha = quickActionsAlpha
                    },
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    horizontalAlignment = Alignment.End
                ) {
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

        // ── 4. Destination Arrival Celebration Modal ───────────────────
        ArrivalCard(
            telemetry = telemetry,
            onDismiss = {
                TelemetryStore.clearActiveRoute()
            },
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .navigationBarsPadding()
                .padding(bottom = 128.dp)
        )

        // ── 5. Bottom Sheet Area & Speed HUD ───────────────────────────
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
                tunnelOverride = telemetry.tunnelOverride,
                onSetTunnelOverride = onSetTunnelOverride,
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

    val pillBg = if (active) palette.primary.copy(alpha = 0.25f) else palette.glassSurface
    val pillBorder = if (active) palette.primary else palette.glassBorder

    Box(
        modifier = Modifier
            .size(42.dp)
            .scale(scale)
            .glassmorphic(
                shape = CircleShape,
                backgroundColor = pillBg,
                borderWidth = 1.dp,
                borderColor = pillBorder,
                glowColor = Color.Transparent,
                glowRadius = 4.dp
            )
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = onClick
            ),
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

package com.sih.idr.demo.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.DarkMode
import androidx.compose.material.icons.rounded.GpsFixed
import androidx.compose.material.icons.rounded.LightMode
import androidx.compose.material.icons.rounded.Navigation
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.TelemetryStore
import com.sih.idr.demo.backend.routing.GeoCoordinate
import com.sih.idr.demo.backend.routing.RouteService
import com.sih.idr.demo.backend.tunnel.TunnelOverride
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.ui.LocalIDRPalette
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
    val density = LocalDensity.current
    val scope = rememberCoroutineScope()
    val tunnelState = telemetry.tunnelState
    val inTunnel = tunnelState == TunnelState.TUNNEL_ACTIVE_IDR || telemetry.tunnelModeActive
    val activeRoute = telemetry.activeRoute
    var isSearchExpanded by remember { mutableStateOf(false) }
    var isSheetExpanded by remember { mutableStateOf(false) }

    // The bottom chrome (speed HUD + sheet) is measured, not assumed: the sheet roughly triples
    // in height when the diagnostics drawer opens, and anything anchored to the bottom of the map
    // -- the arrival card, the map's own Re-center pill -- has to clear whatever height it has.
    var bottomChromeHeightPx by remember { mutableIntStateOf(0) }
    val bottomChromeHeight = with(density) { bottomChromeHeightPx.toDp() }

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
            bottomInset = bottomChromeHeight,
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
            if (activeRoute != null) {
                // A. Active Turn-by-Turn Navigation Header
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

                // Tunnel guidance banner only when tunnel FSM is active and without active route
                if (tunnelState != TunnelState.GNSS_HEALTHY) {
                    GuidanceBanner(
                        telemetry = telemetry,
                        courseUpMode = courseUpMode
                    )
                }
            }

            // The tunnel strip is the same with or without a route: the machine does not know
            // whether a destination was picked, and the DESK_RUN checklist reads these chips on
            // the idle screen (Steps 1, 2 and 4).
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

            HazardChips(
                telemetry = telemetry,
                modifier = Modifier.fillMaxWidth()
            )

            // Stage 5: Measured exit summary toast after GNSS returns (D-124)
            ReconvergenceToast(summary = telemetry.lastExit)

            // ── 3. Floating Quick Action Controls (Right-side column) ──────
            // Flow naturally below whichever top cards / banners are visible so they never
            // overlap. They step aside with the open drawer: the map is a sliver then, and its
            // own zoom capsule rises into this column.
            AnimatedVisibility(
                visible = !isSearchExpanded && !isSheetExpanded,
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

                    // Dark Mode / Light Mode Toggle Button. The icon follows the user's choice,
                    // not the palette on screen: the tunnel palette overrides it and reverts.
                    FloatingActionPill(
                        icon = if (darkTheme) Icons.Rounded.LightMode else Icons.Rounded.DarkMode,
                        contentDescription = if (darkTheme) "Switch to light theme" else "Switch to dark theme",
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
                .padding(bottom = bottomChromeHeight)
        )

        // ── 5. Bottom Sheet Area & Speed HUD ───────────────────────────
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .onSizeChanged { bottomChromeHeightPx = it.height }
        ) {
            // Speed HUD placed bottom-left directly above the bottom sheet (D-081). It exists only
            // while the estimator is producing a speed: before Start there is no reading, and a
            // gauge at zero is a reading (D-080). The open drawer carries the same speed on its
            // first card, so the HUD steps aside rather than ride the sheet up into the banner.
            if (telemetry.running && !isSheetExpanded) {
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
            }

            NavigationBottomSheet(
                telemetry = telemetry,
                isRecording = isRecording,
                permissionsGranted = permissionsGranted,
                isExpanded = isSheetExpanded,
                onExpandedChange = { isSheetExpanded = it },
                tunnelOverride = telemetry.tunnelOverride,
                onSetTunnelOverride = onSetTunnelOverride,
                onStartStop = {
                    // Stopping the recording ends the trip with it; a route with no estimator
                    // behind it would sit on screen with a countdown that never moves.
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

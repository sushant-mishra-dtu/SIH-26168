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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.MotionMode
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.routing.NavigationRoute
import com.sih.idr.demo.backend.tunnel.TunnelOverride
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.LocalIsDarkTheme
import com.sih.idr.demo.ui.glassmorphic
import com.sih.idr.demo.ui.verticalSwipe
import com.sih.idr.demo.ui.glassBorderBrush
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.roundToInt

/**
 * What is steering the traced track right now (D-127), for the diagnostics drawer.
 *
 * The two bugs this chip exists to make visible were both silent on screen. A heading that was
 * really the phone's own azimuth looked exactly like a heading that was the vehicle's course, and
 * the only symptom was that the map turned when the handset did. "Course" means the heading is
 * GNSS-anchored and the phone's attitude is not steering anything; "phone azimuth" means no GNSS
 * course has been seen yet and the heading is still a guess; "held" means the phone is being
 * handled and the course is deliberately frozen.
 */
internal fun headingSourceLabel(
    headingIsCourse: Boolean,
    attitudeDisturbed: Boolean
): String = when {
    attitudeDisturbed -> "held"
    headingIsCourse -> "course"
    else -> "phone azimuth"
}

/** The learned mount offset in whole degrees, or null before there is one to show. */
internal fun mountOffsetLabel(mountOffsetRad: Float?): String? {
    if (mountOffsetRad == null) return null
    val deg = Math.toDegrees(mountOffsetRad.toDouble()).roundToInt()
    return "mount ${if (deg > 0) "+" else ""}$deg°"
}

/** Which motion model is running, or null while the estimator has not committed to one. */
internal fun motionModeLabel(mode: MotionMode): String? = when (mode) {
    MotionMode.VEHICLE -> "vehicle"
    MotionMode.PEDESTRIAN -> "on foot"
    MotionMode.UNKNOWN -> null
}

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
    modifier: Modifier = Modifier,
    isExpanded: Boolean = false,
    onExpandedChange: (Boolean) -> Unit = {},
    tunnelOverride: TunnelOverride = TunnelOverride.AUTO,
    onSetTunnelOverride: (TunnelOverride) -> Unit = {}
) {
    val palette = LocalIDRPalette.current
    val isDark = LocalIsDarkTheme.current
    // The sheet may not swallow the map: the drawer scrolls inside a cap instead of pushing
    // the banner off the top of a phone-sized screen.
    val maxSheetHeight = (LocalConfiguration.current.screenHeightDp * 0.58f).dp

    Box(
        modifier = modifier
            .fillMaxWidth()
            .glassmorphic(
                shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
                backgroundColor = palette.glassSurface,
                borderBrush = glassBorderBrush(isDark = isDark, primaryColor = palette.primary),
                borderWidth = 1.dp,
                glowColor = palette.glassGlow,
                glowRadius = 8.dp
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = maxSheetHeight)
                .navigationBarsPadding()
                .padding(horizontal = 20.dp, vertical = 12.dp)
        ) {
            // The handle and the summary row are one swipe surface: up opens the drawer,
            // down closes it, a tap on the handle toggles. The drawer itself is left out so
            // its own scroll does not fight the gesture.
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalSwipe(
                        onSwipeUp = { onExpandedChange(true) },
                        onSwipeDown = { onExpandedChange(false) }
                    )
            ) {
            // ── Drag Handle / Expand Toggle ────────────────────────────
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onExpandedChange(!isExpanded) }
                    .padding(vertical = 4.dp),
                horizontalArrangement = Arrangement.Center
            ) {
                Box(
                    modifier = Modifier
                        .width(40.dp)
                        .height(4.dp)
                        .background(palette.textSecondary.copy(alpha = 0.45f), CircleShape)
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
                        // Live dynamic route distance, ETA and arrival time
                        val liveDistanceM = telemetry.remainingDistanceM ?: activeRoute.distanceMeters
                        val liveDurationSec = telemetry.remainingDurationSec ?: activeRoute.durationSeconds
                        val liveMinutes = (liveDurationSec / 60).coerceAtLeast(1)
                        val liveEtaStr = if (liveMinutes < 60) {
                            "$liveMinutes min"
                        } else {
                            val hours = liveMinutes / 60
                            val remMin = liveMinutes % 60
                            if (remMin > 0) "$hours hr $remMin min" else "$hours hr"
                        }
                        val liveDistStr = if (liveDistanceM < 1000f) {
                            "${liveDistanceM.roundToInt()} m"
                        } else {
                            "%.1f km".format(Locale.US, liveDistanceM / 1000f)
                        }
                        val arrivalEpochMs = System.currentTimeMillis() + (liveDurationSec * 1000L)
                        val sdf = remember { SimpleDateFormat("h:mm a", Locale.getDefault()) }
                        val liveArrivalClock = sdf.format(Date(arrivalEpochMs))

                        // ETA on its own line; distance, arrival clock and destination share
                        // the next so nothing wraps beside the headline on a 360 dp screen.
                        Text(
                            text = liveEtaStr,
                            style = MaterialTheme.typography.headlineMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontSize = 26.sp
                            ),
                            color = palette.navGreen,
                            maxLines = 1
                        )

                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Text(
                                text = "$liveDistStr · $liveArrivalClock · ${activeRoute.destinationName}",
                                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
                                color = palette.textSecondary,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f, fill = false)
                            )

                            if (telemetry.isOffRoute) {
                                Box(
                                    modifier = Modifier
                                        .background(Color(0xFFD97706), RoundedCornerShape(8.dp))
                                        .padding(horizontal = 6.dp, vertical = 2.dp)
                                ) {
                                    Text(
                                        text = "Off route",
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 10.sp
                                        ),
                                        color = Color.White
                                    )
                                }
                            }
                        }
                    } else {
                        // Free Map Browsing / Active Recording State
                        Text(
                            text = if (telemetry.running) "Navigating" else "Ready",
                            style = MaterialTheme.typography.headlineSmall.copy(
                                fontWeight = FontWeight.Bold
                            ),
                            color = if (telemetry.running) palette.primary else palette.textPrimary,
                            maxLines = 1
                        )

                        val logged = telemetry.totalDistanceM
                        val loggedStr = when {
                            logged < 0.5f -> null
                            logged < 1000f -> "${logged.roundToInt()} m logged"
                            else -> "%.1f km logged".format(Locale.US, logged / 1000f)
                        }
                        Text(
                            text = when {
                                telemetry.running && loggedStr != null -> "Dead reckoning · $loggedStr"
                                telemetry.running -> "IDR dead-reckoning engine active"
                                !permissionsGranted -> "Location access is needed before recording can start"
                                else -> "Pick a destination or tap Start"
                            },
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
                        onClick = { onExpandedChange(!isExpanded) },
                        modifier = Modifier
                            .size(44.dp)
                            .glassmorphic(
                                shape = CircleShape,
                                backgroundColor = palette.glassSurface,
                                borderBrush = glassBorderBrush(isDark = isDark, primaryColor = palette.primary),
                                borderWidth = 1.dp,
                                glowColor = if (isExpanded) palette.glassGlow else Color.Transparent,
                                glowRadius = 4.dp
                            )
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

                    // The button reads the recording, and only the recording: a route chosen
                    // before Start is not something to stop, and a "Stop" that started the
                    // service is the wrong verb on the wrong button. With no permission it is
                    // the one way to ask for it, so it stays enabled and says so.
                    val isStopState = isRecording
                    val buttonBg by animateColorAsState(
                        targetValue = if (isStopState) palette.statusError else palette.primary,
                        animationSpec = spring(stiffness = 400f),
                        label = "btn_bg"
                    )

                    Button(
                        onClick = onStartStop,
                        interactionSource = interactionSource,
                        modifier = Modifier
                            .height(48.dp)
                            .scale(scale),
                        shape = RoundedCornerShape(24.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = buttonBg,
                            disabledContainerColor = palette.textDim.copy(alpha = 0.5f)
                        ),
                        elevation = ButtonDefaults.buttonElevation(defaultElevation = 0.dp)
                    ) {
                        Text(
                            text = when {
                                isStopState -> "Stop"
                                !permissionsGranted -> "Allow location"
                                else -> "Start"
                            },
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = if (isDark && !isStopState) Color(0xFF0F172A) else Color.White
                        )
                    }
                }
            }

            } // swipe surface

            // ── Tier 2: Expandable Technical Diagnostics Drawer ─────────
            AnimatedVisibility(
                visible = isExpanded,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
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

                        // What is steering the track, and what the phone's angle is doing about it
                        // (D-127). Every part is a `TelemetryState` field, not a derived quantity.
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(bottom = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Rounded.Explore,
                                contentDescription = null,
                                modifier = Modifier.size(14.dp),
                                tint = if (telemetry.attitudeDisturbed) palette.statusWarn else palette.primary
                            )
                            val parts = listOfNotNull(
                                headingSourceLabel(telemetry.headingIsCourse, telemetry.attitudeDisturbed),
                                mountOffsetLabel(telemetry.mountOffsetRad),
                                motionModeLabel(telemetry.motionMode)
                            )
                            Text(
                                text = parts.joinToString(" · "),
                                style = MaterialTheme.typography.labelSmall,
                                color = if (telemetry.attitudeDisturbed) palette.statusWarn else palette.textSecondary,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }

                    Spacer(Modifier.height(8.dp))

                    // Tunnel Simulation Override Control (D-126)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "TUNNEL OVERRIDE",
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    letterSpacing = 0.8.sp
                                ),
                                color = palette.textSecondary
                            )
                            Text(
                                text = if (isRecording) "Pin or release GNSS suppression" else "Available while recording",
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = palette.textDim
                            )
                        }

                        TunnelOptionsSelector(
                            currentOverride = tunnelOverride,
                            enabled = isRecording,
                            onSelect = onSetTunnelOverride
                        )
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

@Composable
private fun TunnelOptionsSelector(
    currentOverride: TunnelOverride,
    enabled: Boolean,
    onSelect: (TunnelOverride) -> Unit,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val disabledAlpha by animateFloatAsState(
        targetValue = if (enabled) 1f else 0.4f,
        animationSpec = spring(stiffness = 300f),
        label = "tunnel_selector_alpha"
    )

    Box(
        modifier = modifier
            .alpha(disabledAlpha)
            .glassmorphic(
                shape = RoundedCornerShape(18.dp),
                backgroundColor = palette.glassSurface,
                borderWidth = 1.dp,
                borderColor = palette.glassBorder,
                glowColor = Color.Transparent,
                glowRadius = 4.dp
            )
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 3.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(2.dp)
        ) {
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
        targetValue = if (selected) activeColor.copy(alpha = 0.20f) else Color.Transparent,
        animationSpec = spring(dampingRatio = 0.8f, stiffness = 300f),
        label = "segment_bg_$label"
    )
    val borderColor by animateColorAsState(
        targetValue = if (selected) activeColor.copy(alpha = 0.80f) else Color.Transparent,
        animationSpec = spring(dampingRatio = 0.8f, stiffness = 300f),
        label = "segment_border_$label"
    )
    val textColor by animateColorAsState(
        targetValue = if (selected) activeColor else palette.textSecondary,
        animationSpec = spring(dampingRatio = 0.8f, stiffness = 300f),
        label = "segment_text_$label"
    )

    Box(
        modifier = Modifier
            .scale(scale)
            .clip(RoundedCornerShape(12.dp))
            .background(bgColor)
            .border(1.dp, borderColor, RoundedCornerShape(12.dp))
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                enabled = enabled,
                onClick = onClick
            )
            .padding(horizontal = 8.dp, vertical = 5.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(
                fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium
            ),
            color = textColor
        )
    }
}

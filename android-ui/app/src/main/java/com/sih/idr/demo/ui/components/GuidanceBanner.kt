package com.sih.idr.demo.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.NearMe
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.NavigationMode
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.LocalIsDarkTheme
import com.sih.idr.demo.ui.glassmorphic
import kotlin.math.roundToInt

/**
 * Direction label computed from filter yaw heading in radians.
 *
 * Internal so it can be verified directly by unit tests in `app/src/test`.
 */
internal fun headingToDirection(yawRad: Float): String {
    val deg = Math.toDegrees(yawRad.toDouble()).let { (it % 360 + 360) % 360 }
    val directions = arrayOf("North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West")
    val index = (((deg + 22.5) / 45).toInt()) % 8
    return "Heading ${directions[index]} (${deg.roundToInt()}°)"
}

/**
 * State-driven navigation guidance banner reflecting the autonomous tunnel machine (D-126).
 *
 * This is not a route maneuver banner (the OSM flavour carries no route engine); it renders
 * what is measured on-device from the autonomous tunnel state machine and bundled asset geometry (R-F).
 */
@Composable
fun GuidanceBanner(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier,
    courseUpMode: Boolean = false
) {
    val palette = LocalIDRPalette.current
    val isDark = LocalIsDarkTheme.current
    val tunnelState = telemetry.tunnelState
    // Before Start there is no estimator, so there is no mode: the pill says so instead of
    // borrowing the inertial-coast look for a screen with no data behind it.
    val isIns = telemetry.running &&
        (telemetry.mode == NavigationMode.INS || tunnelState != TunnelState.GNSS_HEALTHY)

    // Determine primary and secondary banner content by tunnel state and map-matched fix (R-F).
    val (primaryText, secondaryText) = when {
        !telemetry.running -> {
            "IDR Navigator" to "Ready to navigate • Tap Start"
        }
        tunnelState == TunnelState.TUNNEL_ACTIVE_IDR -> {
            val primary = if (telemetry.tunnelForced) "In tunnel · inertial (forced)" else "In tunnel · inertial"
            val secondary = if (telemetry.tunnelFix?.inside == true) {
                "Exit in ${telemetry.tunnelFix.remainingM.roundToInt()} m"
            } else {
                "Exit distance unknown"
            }
            primary to secondary
        }
        tunnelState == TunnelState.EXIT_VERIFICATION -> {
            val accepted = telemetry.outageAcceptedFixes
            val total = accepted + telemetry.outageRejectedFixes
            "Checking GNSS" to "$accepted/$total fixes passed"
        }
        tunnelState == TunnelState.SEAMLESS_RECONVERGENCE -> {
            "GNSS re-acquired" to "blending"
        }
        tunnelState == TunnelState.PRE_ARMED_ENTRY -> {
            val fix = telemetry.tunnelFix
            val dist = fix?.distanceToEntryM
            if (fix != null && dist != null && dist <= 500.0) {
                val rounded = (dist / 10.0).roundToInt() * 10
                "Tunnel ahead" to "${fix.tunnel.name} · $rounded m"
            } else {
                "Tunnel ahead" to "Exit distance unknown"
            }
        }
        tunnelState == TunnelState.GNSS_HEALTHY -> {
            val fix = telemetry.tunnelFix
            val dist = fix?.distanceToEntryM
            if (fix != null && dist != null && dist <= 500.0) {
                val rounded = (dist / 10.0).roundToInt() * 10
                "Tunnel ahead" to "${fix.tunnel.name} · $rounded m"
            } else {
                val distKm = telemetry.totalDistanceM / 1000f
                val durSec = telemetry.tripDurationSec
                val timeStr = if (durSec >= 60) "${durSec / 60}m ${durSec % 60}s" else "${durSec}s"
                headingToDirection(telemetry.yawRad) to "%.2f km traveled • $timeStr".format(distKm)
            }
        }
        else -> {
            "IDR Navigator" to "Ready to navigate • Tap Start"
        }
    }

    // Banner background colour animated across state transitions:
    // Keep existing green for GNSS_HEALTHY and SEAMLESS_RECONVERGENCE; amber for PRE_ARMED_ENTRY
    // and EXIT_VERIFICATION; deep navy (dark) / slate (light) for TUNNEL_ACTIVE_IDR.
    val targetBgColor = when (tunnelState) {
        TunnelState.GNSS_HEALTHY, TunnelState.SEAMLESS_RECONVERGENCE ->
            if (isDark) Color(0xFF064E3B) else Color(0xFF0F9D58)
        TunnelState.PRE_ARMED_ENTRY, TunnelState.EXIT_VERIFICATION ->
            if (isDark) Color(0xFF78350F) else palette.statusWarn
        TunnelState.TUNNEL_ACTIVE_IDR ->
            if (isDark) Color(0xFF0F172A) else Color(0xFF334155)
    }
    val animatedBgColor by animateColorAsState(
        targetValue = if (!telemetry.running) (if (isDark) Color(0xFF064E3B) else Color(0xFF0F9D58)) else targetBgColor,
        animationSpec = spring(stiffness = 300f),
        label = "guidance_banner_bg"
    )

    val bannerGlowColor = when {
        !telemetry.running -> Color.Transparent
        tunnelState == TunnelState.TUNNEL_ACTIVE_IDR -> Color(0x3300E5FF)
        tunnelState == TunnelState.EXIT_VERIFICATION -> Color(0x33F59E0B)
        tunnelState == TunnelState.SEAMLESS_RECONVERGENCE -> Color(0x3310B981)
        else -> Color(0x1A000000)
    }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .glassmorphic(
                shape = RoundedCornerShape(20.dp),
                backgroundColor = animatedBgColor.copy(alpha = if (isDark) 0.88f else 0.94f),
                borderWidth = 1.dp,
                borderColor = if (isDark) Color(0x4D38BDF8) else Color(0x33FFFFFF),
                glowColor = bannerGlowColor,
                glowRadius = 8.dp
            )
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
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(Color.White.copy(alpha = 0.22f))
                        .border(1.dp, Color.White.copy(alpha = 0.35f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Rounded.NearMe,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier
                            .size(26.dp)
                            .rotate(animatedHeading)
                    )
                }

                // Guidance text
                Column {
                    Text(
                        text = primaryText,
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = Color.White
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(
                        text = secondaryText,
                        style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp),
                        color = Color.White.copy(alpha = 0.85f)
                    )
                }
            }

            // Status Pill (GNSS Lock vs INS Coasting)
            val pillTint = when {
                isIns -> Color(0xFFFBBF24)
                !telemetry.running -> Color.White.copy(alpha = 0.6f)
                else -> Color(0xFF34D399)
            }
            Surface(
                color = pillTint.copy(alpha = 0.2f),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.border(1.dp, pillTint, RoundedCornerShape(14.dp))
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
                            text = when {
                                tunnelState == TunnelState.GNSS_HEALTHY -> "INS Coast"
                                telemetry.tunnelForced -> "${tunnelState.label} (forced)"
                                else -> tunnelState.label
                            },
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                            color = Color(0xFFFDE68A)
                        )
                    } else if (!telemetry.running) {
                        Text(
                            "Not recording",
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                            color = Color.White.copy(alpha = 0.85f)
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
}

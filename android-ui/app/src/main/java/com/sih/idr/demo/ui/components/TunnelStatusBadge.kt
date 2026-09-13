package com.sih.idr.demo.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.GpsOff
import androidx.compose.material.icons.rounded.Sensors
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.glassmorphic
import kotlin.math.roundToInt

/**
 * Non-intrusive floating status pill indicating active GPS-denied inertial navigation.
 * Displayed dynamically when tunnel mode engages instead of an obstructive full-screen takeover.
 */
@Composable
fun TunnelStatusBadge(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val inTunnel = telemetry.tunnelState == TunnelState.TUNNEL_ACTIVE_IDR || telemetry.tunnelModeActive

    AnimatedVisibility(
        visible = inTunnel,
        enter = fadeIn() + slideInVertically { -it / 2 },
        exit = fadeOut() + slideOutVertically { -it / 2 },
        modifier = modifier
    ) {
        Box(
            modifier = Modifier
                .glassmorphic(
                    shape = RoundedCornerShape(24.dp),
                    backgroundColor = palette.glassSurface,
                    borderWidth = 1.2.dp,
                    borderColor = Color(0xFFD97706).copy(alpha = 0.85f),
                    glowColor = Color(0x33D97706),
                    glowRadius = 8.dp
                )
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Pulse dot / sensor icon
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .background(Color(0xFFD97706).copy(alpha = 0.20f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Rounded.Sensors,
                        contentDescription = "Inertial dead reckoning active",
                        tint = Color(0xFFF59E0B),
                        modifier = Modifier.size(16.dp)
                    )
                }

                Column {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Text(
                            text = "Tunnel Mode · Inertial Dead Reckoning",
                            style = MaterialTheme.typography.labelMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontSize = 12.sp
                            ),
                            color = Color(0xFFF59E0B)
                        )

                        Icon(
                            imageVector = Icons.Rounded.GpsOff,
                            contentDescription = "GNSS Denied",
                            tint = Color(0xFFF59E0B).copy(alpha = 0.8f),
                            modifier = Modifier.size(12.dp)
                        )
                    }

                    val infoText = buildString {
                        append("GNSS denied · InEKF propagating")
                        telemetry.tunnelFix?.let { fix ->
                            if (fix.inside && fix.alongM > 0.0) {
                                append(" · ${fix.alongM.roundToInt()} m in tunnel")
                            }
                        }
                    }

                    Text(
                        text = infoText,
                        style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                        color = palette.textSecondary
                    )
                }
            }
        }
    }
}

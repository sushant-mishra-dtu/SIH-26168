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
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Place
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.ui.LocalIDRPalette
import java.util.Locale
import kotlin.math.roundToInt

/**
 * Consumer-grade celebratory card displayed when the vehicle arrives at the target destination.
 */
@Composable
fun ArrivalCard(
    telemetry: TelemetryState,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val route = telemetry.activeRoute ?: return

    AnimatedVisibility(
        visible = telemetry.hasArrivedAtDestination,
        enter = fadeIn() + slideInVertically { it / 2 },
        exit = fadeOut() + slideOutVertically { it / 2 },
        modifier = modifier
    ) {
        Surface(
            color = palette.bgSheet,
            shape = RoundedCornerShape(24.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp)
                .shadow(16.dp, RoundedCornerShape(24.dp), spotColor = Color(0xFF10B981))
                .border(1.5.dp, Color(0xFF10B981).copy(alpha = 0.8f), RoundedCornerShape(24.dp))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                // Celebration Icon
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .background(Color(0xFF10B981).copy(alpha = 0.18f), CircleShape)
                        .border(1.5.dp, Color(0xFF10B981), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Rounded.CheckCircle,
                        contentDescription = "Arrived",
                        tint = Color(0xFF10B981),
                        modifier = Modifier.size(32.dp)
                    )
                }

                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "You Have Arrived!",
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 22.sp
                        ),
                        color = palette.textPrimary
                    )

                    Spacer(Modifier.height(4.dp))

                    Text(
                        text = route.destinationName,
                        style = MaterialTheme.typography.bodyMedium.copy(
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 15.sp
                        ),
                        color = Color(0xFF10B981)
                    )
                }

                // Trip stats summary row
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(palette.bgCard, RoundedCornerShape(16.dp))
                        .padding(horizontal = 16.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "Distance",
                            style = MaterialTheme.typography.labelSmall,
                            color = palette.textSecondary
                        )
                        val totalDist = telemetry.totalDistanceM
                        val distStr = if (totalDist < 1000f) {
                            "${totalDist.roundToInt()} m"
                        } else {
                            "%.1f km".format(Locale.US, totalDist / 1000f)
                        }
                        Text(
                            text = distStr,
                            style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
                            color = palette.textPrimary
                        )
                    }

                    Box(
                        modifier = Modifier
                            .width(1.dp)
                            .height(24.dp)
                            .background(palette.border)
                    )

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "Duration",
                            style = MaterialTheme.typography.labelSmall,
                            color = palette.textSecondary
                        )
                        val durMin = (telemetry.tripDurationSec / 60).coerceAtLeast(1)
                        Text(
                            text = "$durMin min",
                            style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
                            color = palette.textPrimary
                        )
                    }

                    Box(
                        modifier = Modifier
                            .width(1.dp)
                            .height(24.dp)
                            .background(palette.border)
                    )

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "Tracking",
                            style = MaterialTheme.typography.labelSmall,
                            color = palette.textSecondary
                        )
                        Text(
                            text = "InEKF",
                            style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
                            color = Color(0xFF38BDF8)
                        )
                    }
                }

                // Done Button
                Button(
                    onClick = onDismiss,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(24.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981))
                ) {
                    Text(
                        text = "Done",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = Color.White
                    )
                }
            }
        }
    }
}

package com.sih.idr.demo.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.tunnel.TunnelFix
import com.sih.idr.demo.ui.LocalIDRPalette
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * Tunnel exit progress bar shown during active dead-reckoning inside a mapped tunnel (D-126).
 *
 * Draws progress along the tunnel centreline and projected time to exit based on
 * current estimated forward speed.
 */
@Composable
fun ExitProgressBar(
    fix: TunnelFix,
    speedMps: Float,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val targetFraction = if (fix.tunnel.lengthM > 0.0) {
        (fix.alongM / fix.tunnel.lengthM).toFloat().coerceIn(0f, 1f)
    } else {
        0f
    }
    val animatedFraction by animateFloatAsState(
        targetValue = targetFraction,
        animationSpec = spring(stiffness = 300f),
        label = "exit_progress_fraction"
    )

    val alongM = fix.alongM.roundToInt()
    val lengthM = fix.tunnel.lengthM.roundToInt()
    val leftLabel = "$alongM m / $lengthM m"

    val rightLabel = if (speedMps > 1.0f) {
        val rawT = fix.remainingM / speedMps
        val tSec = max(0, (rawT / 5.0).roundToInt() * 5)
        "Exit in ~${tSec}s"
    } else {
        "stopped"
    }

    Surface(
        color = palette.bgCard.copy(alpha = 0.95f),
        shape = RoundedCornerShape(16.dp),
        modifier = modifier
            .fillMaxWidth()
            .shadow(6.dp, RoundedCornerShape(16.dp), spotColor = Color.Black.copy(alpha = 0.25f))
            .border(1.dp, palette.border, RoundedCornerShape(16.dp))
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = leftLabel,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, fontSize = 12.sp),
                    color = palette.textPrimary
                )
                Text(
                    text = rightLabel,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, fontSize = 12.sp),
                    color = palette.textSecondary
                )
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(palette.border.copy(alpha = 0.6f))
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(animatedFraction)
                        .fillMaxHeight()
                        .clip(RoundedCornerShape(3.dp))
                        .background(palette.primary)
                )
            }
        }
    }
}

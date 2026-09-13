package com.sih.idr.demo.ui.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.glassmorphic
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.roundToInt
import kotlin.math.sin

/**
 * Geometric constants for the circular speedometer arc gauge (D-081).
 *
 * Arc starts at 150° (bottom-left) and sweeps 240° clockwise to 390° (30°, bottom-right),
 * leaving a 120° opening at the bottom.
 */
internal object SpeedGaugeConstants {
    const val START_ANGLE_DEG = 150f
    const val SWEEP_ANGLE_DEG = 240f
    const val MAX_SPEED_KMH = 120f
}

internal fun speedMpsToKmh(speedMps: Float): Float = max(0f, speedMps * 3.6f)

internal fun isSpeedOverLimit(speedKmh: Float, postedLimitKmh: Int?): Boolean =
    postedLimitKmh != null && speedKmh > postedLimitKmh

internal fun speedToGaugeFraction(speedKmh: Float, maxKmh: Float = SpeedGaugeConstants.MAX_SPEED_KMH): Float =
    (speedKmh / maxKmh).coerceIn(0f, 1f)

internal fun limitTickAngleDeg(
    limitKmh: Int,
    maxKmh: Float = SpeedGaugeConstants.MAX_SPEED_KMH,
    startAngleDeg: Float = SpeedGaugeConstants.START_ANGLE_DEG,
    sweepAngleDeg: Float = SpeedGaugeConstants.SWEEP_ANGLE_DEG
): Float = startAngleDeg + (limitKmh.toFloat() / maxKmh).coerceIn(0f, 1f) * sweepAngleDeg

/**
 * Circular speedometer HUD displaying dead-reckoning filter forward speed (D-081).
 *
 * Visual spec:
 * - 96.dp circle with a 240° arc gauge (0..120 km/h), needle-less (filled arc).
 * - Center: integer km/h and "km/h" caption.
 * - Sub-caption (10.sp): "filter speed" explicitly stating what produced the reading (D-081).
 * - If [postedLimitKmh] is non-null, a tick is drawn on the arc at the limit position, and the
 *   filled arc turns amber when speed exceeds the limit.
 */
@Composable
fun SpeedHud(
    speedMps: Float,
    postedLimitKmh: Int?,
    modifier: Modifier = Modifier,
    /** Tapping the gauge; the screen opens the drawer whose first card is this same speed. */
    onClick: (() -> Unit)? = null
) {
    val palette = LocalIDRPalette.current
    val speedKmh = speedMpsToKmh(speedMps)
    val animatedSpeedKmh by animateFloatAsState(
        targetValue = speedKmh,
        animationSpec = spring(stiffness = 300f),
        label = "speed_hud_anim"
    )

    val isOverLimit = isSpeedOverLimit(animatedSpeedKmh, postedLimitKmh)
    val fraction = speedToGaugeFraction(animatedSpeedKmh)
    val sweepAngle = fraction * SpeedGaugeConstants.SWEEP_ANGLE_DEG
    val arcColor = if (isOverLimit) palette.statusWarn else palette.primary

    Box(
        modifier = modifier
            .size(88.dp)
            .glassmorphic(
                shape = CircleShape,
                backgroundColor = palette.glassSurface,
                borderWidth = 1.dp,
                borderColor = if (isOverLimit) palette.statusWarn else palette.glassBorder
            )
            .then(
                if (onClick != null) Modifier.clickable(onClickLabel = "Open diagnostics", onClick = onClick)
                else Modifier
            ),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .padding(6.dp)
        ) {
            val strokeWidth = 4.5.dp.toPx()
            val diameter = size.minDimension - strokeWidth
            val topLeft = Offset((size.width - diameter) / 2f, (size.height - diameter) / 2f)
            val arcSize = Size(diameter, diameter)

            // Background track arc (sweeps 240° from 150°)
            drawArc(
                color = palette.border.copy(alpha = 0.4f),
                startAngle = SpeedGaugeConstants.START_ANGLE_DEG,
                sweepAngle = SpeedGaugeConstants.SWEEP_ANGLE_DEG,
                useCenter = false,
                topLeft = topLeft,
                size = arcSize,
                style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
            )

            // Active speed filled arc
            if (sweepAngle > 0.5f) {
                drawArc(
                    color = arcColor,
                    startAngle = SpeedGaugeConstants.START_ANGLE_DEG,
                    sweepAngle = sweepAngle,
                    useCenter = false,
                    topLeft = topLeft,
                    size = arcSize,
                    style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                )
            }

            // Posted speed limit tick on the arc
            if (postedLimitKmh != null) {
                val tickDeg = limitTickAngleDeg(postedLimitKmh)
                val tickRad = Math.toRadians(tickDeg.toDouble())
                val center = Offset(size.width / 2f, size.height / 2f)
                val radius = diameter / 2f
                val tickHalfLen = (strokeWidth / 2f) + 2.dp.toPx()

                val cosA = cos(tickRad).toFloat()
                val sinA = sin(tickRad).toFloat()

                val p1 = Offset(
                    center.x + (radius - tickHalfLen) * cosA,
                    center.y + (radius - tickHalfLen) * sinA
                )
                val p2 = Offset(
                    center.x + (radius + tickHalfLen) * cosA,
                    center.y + (radius + tickHalfLen) * sinA
                )

                drawLine(
                    color = if (isOverLimit) palette.statusWarn else palette.textPrimary,
                    start = p1,
                    end = p2,
                    strokeWidth = 2.dp.toPx(),
                    cap = StrokeCap.Round
                )
            }
        }

        // Center speed reading & caption
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(top = 2.dp)
        ) {
            Text(
                text = "${animatedSpeedKmh.roundToInt()}",
                style = MaterialTheme.typography.titleLarge.copy(
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    lineHeight = 24.sp
                ),
                color = if (isOverLimit) palette.statusWarn else palette.textPrimary
            )
            Text(
                text = "km/h",
                style = MaterialTheme.typography.labelSmall.copy(
                    fontSize = 10.sp,
                    fontWeight = FontWeight.SemiBold,
                    lineHeight = 10.sp
                ),
                color = palette.textSecondary
            )
            Text(
                text = "filter speed",
                style = MaterialTheme.typography.labelSmall.copy(
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Normal,
                    lineHeight = 10.sp
                ),
                color = palette.textDim
            )
        }
    }
}

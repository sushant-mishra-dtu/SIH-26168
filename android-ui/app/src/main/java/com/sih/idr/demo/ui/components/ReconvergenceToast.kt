package com.sih.idr.demo.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.sih.idr.demo.backend.TunnelExitSummary
import com.sih.idr.demo.ui.LocalIDRPalette
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

/**
 * Stage 5 of `docs/UI_UX_NAVIGATION_PLAN.md`: the floating summary shown for a few seconds once
 * GNSS is back, rewritten under D-124. Every number is a field of [TunnelExitSummary], which the
 * estimator measured on the device: distance dead-reckoned, outage duration, the residual between
 * the dead-reckoned pose and the first fix the gate let through, and the gate's vote. The plan's
 * original "Filter Drift 3.8 m (0.29 %) - Grade: A" is not here and must not come back: drift is
 * error against truth, a phone has no truth, and a grade on it is self-awarded.
 */
@Composable
fun ReconvergenceToast(
    summary: TunnelExitSummary?,
    modifier: Modifier = Modifier,
    visibleForMs: Long = 6_000L,
) {
    var shown by remember { mutableStateOf<TunnelExitSummary?>(null) }
    LaunchedEffect(summary?.endedAtMs) {
        if (summary == null) return@LaunchedEffect
        shown = summary
        delay(visibleForMs)
        shown = null
    }

    val palette = LocalIDRPalette.current
    AnimatedVisibility(
        visible = shown != null,
        enter = fadeIn() + slideInVertically { -it / 2 },
        exit = fadeOut() + slideOutVertically { -it / 2 },
        modifier = modifier
    ) {
        val s = shown ?: return@AnimatedVisibility
        val forced = s.reacquiredByForce
        val accent = if (forced) palette.statusWarn else palette.statusOk
        Surface(
            color = palette.bgSheet,
            shape = RoundedCornerShape(16.dp),
            shadowElevation = 8.dp,
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, accent.copy(alpha = 0.6f), RoundedCornerShape(16.dp))
        ) {
            Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (forced) Icons.Rounded.Warning else Icons.Rounded.CheckCircle,
                        contentDescription = null,
                        tint = accent,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(Modifier.size(8.dp))
                    Text(
                        text = if (forced) "GPS re-acquired by timeout" else "GPS restored",
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                        color = palette.textPrimary
                    )
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    text = "${s.distanceOnIdrM.roundToInt()} m on IDR · ${formatElapsed(s.elapsedMs)} · " +
                        (s.exitResidualM?.let { "exit residual ${"%.1f".format(it)} m vs GNSS" }
                            ?: "no fix accepted"),
                    style = MaterialTheme.typography.bodySmall,
                    color = palette.textSecondary
                )
                Text(
                    text = "χ² gate: ${s.acceptedFixes} accepted · ${s.rejectedFixes} rejected" +
                        (if (forced) " · applied by the anti-lockout rule, not a pass" else ""),
                    style = MaterialTheme.typography.bodySmall,
                    color = palette.textSecondary
                )
            }
        }
    }
}

private fun formatElapsed(ms: Long): String {
    val s = ms / 1000
    return if (s >= 60) "${s / 60}m ${s % 60}s" else "${s}s"
}

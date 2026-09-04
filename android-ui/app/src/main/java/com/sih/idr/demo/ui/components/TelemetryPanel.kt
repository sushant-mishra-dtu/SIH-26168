package com.sih.idr.demo.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.ui.IDRColors
import kotlin.math.roundToInt

/**
 * Bottom info panel showing 3 metrics in rounded square cards, matching the screenshot style.
 */
@Composable
fun TelemetryPanel(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Card 1: Speed
        val speedKmh = (telemetry.speedMps * 3.6f)
        MetricCard(
            modifier = Modifier.weight(1f),
            value = if (speedKmh < 100) "%.1f".format(speedKmh) else speedKmh.roundToInt().toString(),
            unit = "km/h"
        )

        // Card 2: Drift / Uncertainty
        MetricCard(
            modifier = Modifier.weight(1f),
            value = "±${telemetry.uncertaintyM.roundToInt()}",
            unit = "m drift"
        )

        // Card 3: Satellites
        val satValue = if (telemetry.gnssAvailable) telemetry.satellites.toString() else "0"
        MetricCard(
            modifier = Modifier.weight(1f),
            value = satValue,
            unit = "Sats"
        )
    }
}

@Composable
private fun MetricCard(
    value: String,
    unit: String,
    modifier: Modifier = Modifier
) {
    Surface(
        color = IDRColors.BgCard,
        shape = RoundedCornerShape(20.dp),
        modifier = modifier.aspectRatio(1f) // Makes it a square
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.fillMaxSize()
        ) {
            Text(
                text = buildAnnotatedString {
                    // Split if there's a decimal point for styling
                    val parts = value.split(".")
                    if (parts.size == 2) {
                        append(parts[0])
                        withStyle(SpanStyle(fontSize = 18.sp, color = IDRColors.TextSecondary)) {
                            append(".${parts[1]}")
                        }
                    } else {
                        append(value)
                    }
                },
                style = MaterialTheme.typography.displayMedium,
                color = IDRColors.TextPrimary
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = unit,
                style = MaterialTheme.typography.titleSmall,
                color = IDRColors.TextSecondary
            )
        }
    }
}

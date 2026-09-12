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
 * Bottom info panel showing 3 metrics in rounded square cards.
 *
 * **Nothing here is computed and nothing here is invented (D-079, D-080).** Every value is a field
 * of [TelemetryState] as the recording service reported it; the only arithmetic is m/s to km/h,
 * which is a unit, not a quantity. Before a recording starts there is nothing to report, so the
 * cards read "--" rather than a well-formed zero -- a zero is a reading, and this is the absence
 * of one.
 *
 * The middle card was labelled **"m drift"**, which it is not. `uncertaintyM` is the demo
 * estimator's own uncertainty figure; drift is error against a truth trajectory as a percentage of
 * distance travelled, it is the metric PS 26168 is graded on, and this app cannot produce it --
 * there is no truth on a phone. Labelling one as the other puts the graded metric on screen with a
 * number that was never measured against truth behind it.
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
        // Card 1: Speed, as reported.
        val speedKmh = (telemetry.speedMps * 3.6f)
        MetricCard(
            modifier = Modifier.weight(1f),
            value = when {
                !telemetry.running -> NO_READING
                speedKmh < 100 -> "%.1f".format(speedKmh)
                else -> speedKmh.roundToInt().toString()
            },
            unit = "km/h"
        )

        // Card 2: the estimator's own uncertainty. Not drift -- see the note on this file.
        MetricCard(
            modifier = Modifier.weight(1f),
            value = if (telemetry.running) "±${telemetry.uncertaintyM.roundToInt()}" else NO_READING,
            unit = "m est. σ"
        )

        // Card 3: Satellites
        MetricCard(
            modifier = Modifier.weight(1f),
            value = when {
                !telemetry.running -> NO_READING
                telemetry.gnssAvailable -> telemetry.satellites.toString()
                else -> "0"
            },
            unit = "Sats"
        )
    }
}

/** What a card shows when there is no recording behind it. */
private const val NO_READING = "--"

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

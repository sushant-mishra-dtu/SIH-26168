package com.sih.idr.demo.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.ui.IDRColors
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

/**
 * The recorded track, drawn in metres on a plain canvas. **There is no basemap and no tile
 * server.**
 *
 * This was an `osmdroid` map pulling raster tiles from `basemaps.cartocdn.com`. Three things were
 * wrong with that and only the first is obvious:
 *
 *  1. It is a network call at runtime, which D-041's "100% offline" claim does not survive and
 *     which D-080 forbids the demo surface outright.
 *  2. Tiles under a track imply a *fix* to the road. Nothing here matches to a road -- the map
 *     matcher is seat P's October work -- so road geometry beneath the line would be read by a
 *     judge as evidence of something the system does not do yet (HANDOVER.md section 3b).
 *  3. It anchored the track at a hard-coded Delhi origin, which places a recording made anywhere
 *     else on top of streets it was never driven on.
 *
 * What is drawn is what was measured: the track, the marker, the reported uncertainty radius, and
 * a scale bar so distances stay readable without a basemap. Metres to pixels is a projection, not
 * a computed quantity -- no displayed *number* originates here (D-079).
 */
@Composable
fun MapView(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier
) {
    BoxWithConstraints(modifier = modifier.fillMaxSize()) {
        val view = ViewWindow.of(
            telemetry,
            Size(constraints.maxWidth.toFloat(), constraints.maxHeight.toFloat()),
        )

        Canvas(modifier = Modifier.fillMaxSize()) {
            drawGraticule(view)
            drawTrack(telemetry, view)
            drawUncertainty(telemetry, view)
            drawMarker(telemetry, view)
            drawScaleBar(view)
        }

        Text(
            text = "no basemap — offline build. Track in metres from the first fix; " +
                "the line is not matched to a road.",
            style = MaterialTheme.typography.bodySmall,
            color = IDRColors.TextSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(horizontal = 24.dp, vertical = 72.dp)
        )

        Text(
            text = "${view.scaleBarMetres.roundToInt()} m",
            style = MaterialTheme.typography.labelMedium,
            color = IDRColors.TextSecondary,
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(start = 24.dp, bottom = 36.dp)
        )
    }
}

/**
 * The metres-to-pixels mapping for one frame: everything recorded, plus the uncertainty radius,
 * fitted into the canvas with a margin, never zoomed in past [MIN_SPAN_M].
 */
private class ViewWindow(
    val centreNorthM: Float,
    val centreEastM: Float,
    val pixelsPerMetre: Float,
    val canvas: Size,
) {
    fun toPixels(northM: Float, eastM: Float) = Offset(
        // East is +x, north is -y: north is up the screen, and screen y grows downwards.
        x = canvas.width / 2f + (eastM - centreEastM) * pixelsPerMetre,
        y = canvas.height / 2f - (northM - centreNorthM) * pixelsPerMetre,
    )

    /** The round number of metres the scale bar spans at this zoom. */
    val scaleBarMetres: Float
        get() = NICE_SPANS_M.lastOrNull { it * pixelsPerMetre <= canvas.width * 0.3f }
            ?: NICE_SPANS_M.first()

    companion object {
        /** No closer than this, so a stationary phone does not render as a hugely zoomed dot. */
        const val MIN_SPAN_M = 120f
        private const val MARGIN = 0.82f

        val NICE_SPANS_M = listOf(10f, 25f, 50f, 100f, 250f, 500f, 1000f, 2500f)

        fun of(telemetry: TelemetryState, canvas: Size): ViewWindow {
            val norths = telemetry.path.map { it.northM } + telemetry.positionNorthM
            val easts = telemetry.path.map { it.eastM } + telemetry.positionEastM
            val centreNorth = (norths.min() + norths.max()) / 2f
            val centreEast = (easts.min() + easts.max()) / 2f
            // The uncertainty circle is part of the picture, so it has to fit inside it too.
            val spanM = max(
                max(norths.max() - norths.min(), easts.max() - easts.min()) +
                    2f * telemetry.uncertaintyM,
                MIN_SPAN_M,
            )
            val shorterEdge = max(1f, min(canvas.width, canvas.height))
            return ViewWindow(centreNorth, centreEast, shorterEdge * MARGIN / spanM, canvas)
        }
    }
}

/** A 50 m grid, so the scale is legible in the picture and not only in the scale bar. */
private fun DrawScope.drawGraticule(view: ViewWindow) {
    val stepPx = 50f * view.pixelsPerMetre
    if (stepPx < 12f) return
    val colour = IDRColors.TextDim.copy(alpha = 0.35f)
    var x = view.canvas.width / 2f % stepPx
    while (x < view.canvas.width) {
        drawLine(colour, Offset(x, 0f), Offset(x, view.canvas.height), strokeWidth = 1f)
        x += stepPx
    }
    var y = view.canvas.height / 2f % stepPx
    while (y < view.canvas.height) {
        drawLine(colour, Offset(0f, y), Offset(view.canvas.width, y), strokeWidth = 1f)
        y += stepPx
    }
}

private fun DrawScope.drawTrack(telemetry: TelemetryState, view: ViewWindow) {
    val points = telemetry.path
    if (points.size < 2) return
    val path = Path()
    points.forEachIndexed { i, p ->
        val o = view.toPixels(p.northM, p.eastM)
        if (i == 0) path.moveTo(o.x, o.y) else path.lineTo(o.x, o.y)
    }
    drawPath(path, color = IDRColors.Blue, style = Stroke(width = 12f))
}

/**
 * The reported uncertainty radius, exactly as the telemetry reports it. The colour thresholds are
 * presentation; the radius is not recomputed here.
 */
private fun DrawScope.drawUncertainty(telemetry: TelemetryState, view: ViewWindow) {
    val radiusPx = telemetry.uncertaintyM * view.pixelsPerMetre
    if (radiusPx <= 0f) return
    val colour = when {
        telemetry.uncertaintyM < 15f -> IDRColors.GreenOk
        telemetry.uncertaintyM < 40f -> IDRColors.AmberWarn
        else -> IDRColors.RedError
    }
    val centre = view.toPixels(telemetry.positionNorthM, telemetry.positionEastM)
    drawCircle(colour.copy(alpha = 0.12f), radius = radiusPx, center = centre)
    drawCircle(colour.copy(alpha = 0.5f), radius = radiusPx, center = centre, style = Stroke(4f))
}

/** Position and heading, both read from the telemetry. */
private fun DrawScope.drawMarker(telemetry: TelemetryState, view: ViewWindow) {
    val centre = view.toPixels(telemetry.positionNorthM, telemetry.positionEastM)
    drawCircle(Color.White, radius = 20f, center = centre)
    drawCircle(IDRColors.Blue, radius = 15f, center = centre)
    // Yaw is measured clockwise from north, which on screen is +x east and -y north.
    val yaw = telemetry.yawRad
    val tip = Offset(centre.x + 34f * sin(yaw), centre.y - 34f * cos(yaw))
    drawLine(IDRColors.Blue, centre, tip, strokeWidth = 6f)
}

/** Without a basemap this is the only thing that says how big the picture is. */
private fun DrawScope.drawScaleBar(view: ViewWindow) {
    val lengthPx = view.scaleBarMetres * view.pixelsPerMetre
    val y = view.canvas.height - 48f
    val x0 = 48f
    drawLine(IDRColors.TextSecondary, Offset(x0, y), Offset(x0 + lengthPx, y), strokeWidth = 4f)
    drawLine(IDRColors.TextSecondary, Offset(x0, y - 8f), Offset(x0, y + 8f), strokeWidth = 4f)
    drawLine(
        IDRColors.TextSecondary,
        Offset(x0 + lengthPx, y - 8f),
        Offset(x0 + lengthPx, y + 8f),
        strokeWidth = 4f,
    )
}

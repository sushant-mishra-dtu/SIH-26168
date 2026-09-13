package com.sih.idr.demo.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.errorEllipse
import com.sih.idr.demo.ui.LocalIDRPalette
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * 2D projected coordinate on screen. Pure Kotlin data class with zero Compose dependencies
 * so that projection geometry can be tested directly in unit tests without a Compose runtime.
 */
data class ProjectedPoint(val x: Float, val y: Float)

/**
 * Projection and physical geometry constants for the 3D perspective tunnel corridor (D-126).
 *
 * - Camera: fixed chase view, vanishing point at (0.5 w, 0.42 h) leaving ample viewport
 *   in the lower half for the road surface and vehicle puck.
 * - Perspective: f = 12 m focal distance prevents wide-angle barrel distortion.
 * - k: chosen so a standard 3.5 m highway lane occupies 60% of screen width at d = 0.
 * - Eye height: H_EYE_M = 2.4 m models an elevated chase camera behind the vehicle.
 * - Fog horizon: FOG_RANGE_M = 120 m where alpha falls linearly to 0.
 */
internal object CorridorGeometry {
    /** Focal distance in metres for perspective scaling: scale = f / (d + f). */
    const val FOCAL_M = 12.0f

    /** Vanishing point X ratio relative to screen width. */
    const val VP_X_RATIO = 0.50f

    /** Vanishing point Y ratio relative to screen height. */
    const val VP_Y_RATIO = 0.42f

    /** Standard lane width in metres. */
    const val LANE_WIDTH_M = 3.5f

    /** Fraction of screen width occupied by a 3.5 m lane at d = 0. */
    const val LANE_WIDTH_FRACTION = 0.60f

    /** Chase camera eye height above road surface in metres. */
    const val H_EYE_M = 2.4f

    /** Tunnel ceiling height above road surface in metres. */
    const val H_TUNNEL_M = 4.8f

    /** Tunnel half-width from centreline in metres (~8.0 m total road + shoulders). */
    const val ROAD_HALF_WIDTH_M = 4.0f

    /** Half-width of single lane in metres. */
    const val LANE_HALF_WIDTH_M = 1.75f

    /** Depth fog range in metres: alpha decreases linearly from 1 at d=0 to 0 at d=120m. */
    const val FOG_RANGE_M = 120.0f

    /** Ceiling lamp spacing along the tunnel in metres. */
    const val LAMP_SPACING_M = 15.0f

    /** Structural wall arc rib spacing along the tunnel in metres. */
    const val RIB_SPACING_M = 10.0f

    /** Dashed centreline period (dash + gap) in metres. */
    const val DASH_SPACING_M = 6.0f

    /** Dashed centreline dash length in metres. */
    const val DASH_LENGTH_M = 3.0f

    /** Computes lateral scale factor k in pixels per metre for a given screen width. */
    fun k(width: Float): Float = width * (LANE_WIDTH_FRACTION / LANE_WIDTH_M)
}

/**
 * Pure perspective projection function mapping 3D coordinates in tunnel frame to 2D screen coordinates.
 *
 * @param dM Forward distance along tunnel in metres. Clamped to dM >= 0 (no rendering behind camera).
 * @param xM Lateral offset from tunnel centreline in metres (positive right, negative left).
 * @param yM Elevation above road surface in metres (0 = road surface, H_TUNNEL = ceiling).
 * @param w Screen width in pixels.
 * @param h Screen height in pixels.
 */
internal fun project(dM: Float, xM: Float, yM: Float = 0f, w: Float, h: Float): ProjectedPoint {
    val dClamped = max(0f, dM)
    val scale = CorridorGeometry.FOCAL_M / (dClamped + CorridorGeometry.FOCAL_M)
    val k = CorridorGeometry.k(w)
    val vpX = w * CorridorGeometry.VP_X_RATIO
    val vpY = h * CorridorGeometry.VP_Y_RATIO
    val screenX = vpX + xM * scale * k
    val yRel = CorridorGeometry.H_EYE_M - yM
    val screenY = vpY + yRel * scale * k
    return ProjectedPoint(screenX, screenY)
}

/**
 * Jetpack Compose Canvas rendering a perspective 3D tunnel corridor from the vehicle's chase perspective.
 *
 * Every element is driven strictly by [TelemetryState] and bundled tunnel geometry (R-B, R-F).
 * No frame-clock timers, animation loops, or random numbers are used (R-B, R-C).
 */
@Composable
fun TunnelCorridor(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier
) {
    val palette = LocalIDRPalette.current
    val textMeasurer = rememberTextMeasurer()

    // ── Motion Tracking ─────────────────────────────────────────────────────────────
    // Motion advances strictly from TelemetryState poseElapsedMs (R-B).
    // If the pose clock does not advance, nothing moves — that is the intended
    // behaviour at a traffic stop (D-080, R-B). No frame-clock timers or
    // simulated coasting are used.
    var alongM by remember { mutableFloatStateOf(0f) }
    var lastPoseElapsedMs by remember { mutableLongStateOf(0L) }

    val currentPoseElapsedMs = telemetry.poseElapsedMs
    if (lastPoseElapsedMs > 0L && currentPoseElapsedMs > lastPoseElapsedMs) {
        val dtSec = ((currentPoseElapsedMs - lastPoseElapsedMs) / 1000f).coerceIn(0f, 0.5f)
        alongM = (alongM + telemetry.speedMps * dtSec) % 10_000f
    }
    lastPoseElapsedMs = currentPoseElapsedMs

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF080B11)) // Deep obsidian void
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val w = size.width
            val h = size.height
            val fogMax = CorridorGeometry.FOG_RANGE_M
            val vpX = w * CorridorGeometry.VP_X_RATIO
            val vpY = h * CorridorGeometry.VP_Y_RATIO

            // 1. Road Surface Quad (d = 0 to 120 m)
            val roadNearL = project(0f, -CorridorGeometry.ROAD_HALF_WIDTH_M, 0f, w, h)
            val roadNearR = project(0f, CorridorGeometry.ROAD_HALF_WIDTH_M, 0f, w, h)
            val roadFarL = project(fogMax, -CorridorGeometry.ROAD_HALF_WIDTH_M, 0f, w, h)
            val roadFarR = project(fogMax, CorridorGeometry.ROAD_HALF_WIDTH_M, 0f, w, h)

            val roadPath = Path().apply {
                moveTo(roadNearL.x, roadNearL.y)
                lineTo(roadFarL.x, roadFarL.y)
                lineTo(roadFarR.x, roadFarR.y)
                lineTo(roadNearR.x, roadNearR.y)
                close()
            }
            drawPath(
                path = roadPath,
                brush = Brush.verticalGradient(
                    colors = listOf(Color(0xFF0A0F1D), Color(0xFF0F172A)),
                    startY = vpY,
                    endY = roadNearL.y
                ),
                style = Fill
            )

            // 2. Lateral Tunnel Walls (Left and Right)
            val ceilNearL = project(0f, -CorridorGeometry.ROAD_HALF_WIDTH_M, CorridorGeometry.H_TUNNEL_M, w, h)
            val ceilNearR = project(0f, CorridorGeometry.ROAD_HALF_WIDTH_M, CorridorGeometry.H_TUNNEL_M, w, h)
            val ceilFarL = project(fogMax, -CorridorGeometry.ROAD_HALF_WIDTH_M, CorridorGeometry.H_TUNNEL_M, w, h)
            val ceilFarR = project(fogMax, CorridorGeometry.ROAD_HALF_WIDTH_M, CorridorGeometry.H_TUNNEL_M, w, h)

            val leftWallPath = Path().apply {
                moveTo(roadNearL.x, roadNearL.y)
                lineTo(roadFarL.x, roadFarL.y)
                lineTo(ceilFarL.x, ceilFarL.y)
                lineTo(ceilNearL.x, ceilNearL.y)
                close()
            }
            drawPath(
                path = leftWallPath,
                brush = Brush.horizontalGradient(
                    colors = listOf(Color(0xFF070B14), Color(0xFF0D1527)),
                    startX = 0f,
                    endX = roadNearL.x
                ),
                style = Fill
            )

            val rightWallPath = Path().apply {
                moveTo(roadNearR.x, roadNearR.y)
                lineTo(roadFarR.x, roadFarR.y)
                lineTo(ceilFarR.x, ceilFarR.y)
                lineTo(ceilNearR.x, ceilNearR.y)
                close()
            }
            drawPath(
                path = rightWallPath,
                brush = Brush.horizontalGradient(
                    colors = listOf(Color(0xFF0D1527), Color(0xFF070B14)),
                    startX = roadNearR.x,
                    endX = w
                ),
                style = Fill
            )

            // 3. Ceiling Surface
            val ceilingPath = Path().apply {
                moveTo(ceilNearL.x, ceilNearL.y)
                lineTo(ceilFarL.x, ceilFarL.y)
                lineTo(ceilFarR.x, ceilFarR.y)
                lineTo(ceilNearR.x, ceilNearR.y)
                close()
            }
            drawPath(
                path = ceilingPath,
                brush = Brush.verticalGradient(
                    colors = listOf(Color(0xFF05080F), Color(0xFF090E1A)),
                    startY = 0f,
                    endY = vpY
                ),
                style = Fill
            )

            // 4. Longitudinal Boundary Lines
            val wallEdgeAlpha = 0.45f
            drawLine(
                color = Color(0xFF38BDF8).copy(alpha = wallEdgeAlpha),
                start = Offset(roadNearL.x, roadNearL.y),
                end = Offset(roadFarL.x, roadFarL.y),
                strokeWidth = 2.5f
            )
            drawLine(
                color = Color(0xFF38BDF8).copy(alpha = wallEdgeAlpha),
                start = Offset(roadNearR.x, roadNearR.y),
                end = Offset(roadFarR.x, roadFarR.y),
                strokeWidth = 2.5f
            )
            drawLine(
                color = Color(0xFF1E293B).copy(alpha = 0.6f),
                start = Offset(ceilNearL.x, ceilNearL.y),
                end = Offset(ceilFarL.x, ceilFarL.y),
                strokeWidth = 1.5f
            )
            drawLine(
                color = Color(0xFF1E293B).copy(alpha = 0.6f),
                start = Offset(ceilNearR.x, ceilNearR.y),
                end = Offset(ceilFarR.x, ceilFarR.y),
                strokeWidth = 1.5f
            )

            // Lane Edge Markings (solid lines at +- 1.75 m)
            val laneLNear = project(0f, -CorridorGeometry.LANE_HALF_WIDTH_M, 0f, w, h)
            val laneLFar = project(fogMax, -CorridorGeometry.LANE_HALF_WIDTH_M, 0f, w, h)
            val laneRNear = project(0f, CorridorGeometry.LANE_HALF_WIDTH_M, 0f, w, h)
            val laneRFar = project(fogMax, CorridorGeometry.LANE_HALF_WIDTH_M, 0f, w, h)

            drawLine(
                color = Color(0xFF94A3B8).copy(alpha = 0.35f),
                start = Offset(laneLNear.x, laneLNear.y),
                end = Offset(laneLFar.x, laneLFar.y),
                strokeWidth = 1.5f
            )
            drawLine(
                color = Color(0xFF94A3B8).copy(alpha = 0.35f),
                start = Offset(laneRNear.x, laneRNear.y),
                end = Offset(laneRFar.x, laneRFar.y),
                strokeWidth = 1.5f
            )

            // 5. Structural Wall Arc Ribs (every 10 m, placed at n * spacing - alongM mod spacing)
            val ribSpacing = CorridorGeometry.RIB_SPACING_M
            val ribOffset = ((alongM % ribSpacing) + ribSpacing) % ribSpacing
            val maxRibIdx = (fogMax / ribSpacing).toInt() + 1
            for (n in 0..maxRibIdx) {
                val d = n * ribSpacing - ribOffset
                if (d < 0.5f || d > fogMax) continue
                val fog = (1f - d / fogMax).coerceIn(0f, 1f)
                val ribBaseL = project(d, -CorridorGeometry.ROAD_HALF_WIDTH_M, 0f, w, h)
                val ribTopL = project(d, -CorridorGeometry.ROAD_HALF_WIDTH_M, CorridorGeometry.H_TUNNEL_M * 0.85f, w, h)
                val ribApex = project(d, 0f, CorridorGeometry.H_TUNNEL_M, w, h)
                val ribTopR = project(d, CorridorGeometry.ROAD_HALF_WIDTH_M, CorridorGeometry.H_TUNNEL_M * 0.85f, w, h)
                val ribBaseR = project(d, CorridorGeometry.ROAD_HALF_WIDTH_M, 0f, w, h)

                val ribPath = Path().apply {
                    moveTo(ribBaseL.x, ribBaseL.y)
                    lineTo(ribTopL.x, ribTopL.y)
                    quadraticTo(ribTopL.x, ribApex.y, ribApex.x, ribApex.y)
                    quadraticTo(ribTopR.x, ribApex.y, ribTopR.x, ribTopR.y)
                    lineTo(ribBaseR.x, ribBaseR.y)
                }
                val ribScale = CorridorGeometry.FOCAL_M / (d + CorridorGeometry.FOCAL_M)
                drawPath(
                    path = ribPath,
                    color = Color(0xFF38BDF8).copy(alpha = 0.38f * fog),
                    style = Stroke(width = max(1.0f, 2.8f * ribScale))
                )
            }

            // 6. Dashed Centre Line (every 6 m, dash 3 m, placed at n * spacing - alongM mod spacing)
            val dashSpacing = CorridorGeometry.DASH_SPACING_M
            val dashLen = CorridorGeometry.DASH_LENGTH_M
            val dashOffset = ((alongM % dashSpacing) + dashSpacing) % dashSpacing
            val maxDashIdx = (fogMax / dashSpacing).toInt() + 1
            for (n in 0..maxDashIdx) {
                val dStart = n * dashSpacing - dashOffset
                val dEnd = dStart + dashLen
                if (dEnd <= 0f || dStart >= fogMax) continue
                val d0 = max(0f, dStart)
                val d1 = min(fogMax, dEnd)
                val dMid = (d0 + d1) / 2f
                val fog = (1f - dMid / fogMax).coerceIn(0f, 1f)
                val p0 = project(d0, 0f, 0f, w, h)
                val p1 = project(d1, 0f, 0f, w, h)
                val dashScale = CorridorGeometry.FOCAL_M / (dMid + CorridorGeometry.FOCAL_M)

                drawLine(
                    color = Color(0xFFF8FAFC).copy(alpha = 0.85f * fog),
                    start = Offset(p0.x, p0.y),
                    end = Offset(p1.x, p1.y),
                    strokeWidth = max(1.5f, 3.5f * dashScale)
                )
            }

            // 7. Ceiling Lamps (every 15 m, placed at n * spacing - alongM mod spacing)
            val lampSpacing = CorridorGeometry.LAMP_SPACING_M
            val lampOffset = ((alongM % lampSpacing) + lampSpacing) % lampSpacing
            val maxLampIdx = (fogMax / lampSpacing).toInt() + 1
            for (n in 0..maxLampIdx) {
                val d = n * lampSpacing - lampOffset
                if (d < 0.5f || d > fogMax) continue
                val fog = (1f - d / fogMax).coerceIn(0f, 1f)
                val lampPt = project(d, 0f, CorridorGeometry.H_TUNNEL_M, w, h)
                val lampScale = CorridorGeometry.FOCAL_M / (d + CorridorGeometry.FOCAL_M)

                // Halo glow
                drawCircle(
                    color = Color(0xFF38BDF8).copy(alpha = 0.22f * fog),
                    radius = max(3f, 12f * lampScale),
                    center = Offset(lampPt.x, lampPt.y)
                )
                // Crisp core
                drawCircle(
                    color = Color.White.copy(alpha = 0.90f * fog),
                    radius = max(1.5f, 3.5f * lampScale),
                    center = Offset(lampPt.x, lampPt.y)
                )
            }

            // 8. Exit Portal Glow (active only when tunnelFix?.inside == true)
            val fix = telemetry.tunnelFix
            if (fix?.inside == true) {
                val remM = fix.remainingM.toFloat().coerceIn(0f, fogMax)
                val brightness = (1f - remM / fogMax).coerceIn(0f, 1f)
                val exitPt = project(remM, 0f, CorridorGeometry.H_TUNNEL_M * 0.5f, w, h)
                val exitScale = CorridorGeometry.FOCAL_M / (remM + CorridorGeometry.FOCAL_M)
                val k = CorridorGeometry.k(w)
                val glowRadius = max(
                    24f,
                    (CorridorGeometry.ROAD_HALF_WIDTH_M * 1.6f) * exitScale * k * (0.6f + 0.6f * brightness)
                )

                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(0xFFE0F2FE).copy(alpha = 0.75f * brightness),
                            Color(0xFF38BDF8).copy(alpha = 0.35f * brightness),
                            Color.Transparent
                        ),
                        center = Offset(exitPt.x, exitPt.y),
                        radius = glowRadius
                    ),
                    center = Offset(exitPt.x, exitPt.y),
                    radius = glowRadius
                )
            }

            // 9. Vehicle & 1-Sigma Position Uncertainty Ellipse at d = 0
            val vehPos = project(0f, 0f, 0f, w, h)

            if (telemetry.running && telemetry.uncertaintyM > 0f) {
                val ellipse = errorEllipse(
                    covNorthM2 = telemetry.covNorthM2,
                    covNorthEastM2 = telemetry.covNorthEastM2,
                    covEastM2 = telemetry.covEastM2
                )
                val k = CorridorGeometry.k(w)
                val yPitchRatio = CorridorGeometry.H_EYE_M / CorridorGeometry.FOCAL_M
                val relAngle = ellipse.orientationRad - telemetry.yawRad
                val cosRel = cos(relAngle)
                val sinRel = sin(relAngle)
                val numPoints = 40
                val ellipsePath = Path()
                var lowestY = vehPos.y

                for (i in 0 until numPoints) {
                    val t = (2.0 * Math.PI * i / numPoints).toFloat()
                    val uEllipse = ellipse.semiMajorM * cos(t)
                    val vEllipse = ellipse.semiMinorM * sin(t)
                    // Rotate into vehicle body frame (uBody forward, vBody lateral to right)
                    val uBody = uEllipse * cosRel - vEllipse * sinRel
                    val vBody = uEllipse * sinRel + vEllipse * cosRel
                    // Lateral offset is +X, forward offset is -Y (towards vanishing point)
                    val ptX = vehPos.x + vBody * k
                    val ptY = vehPos.y - uBody * k * yPitchRatio
                    if (ptY > lowestY) lowestY = ptY
                    if (i == 0) ellipsePath.moveTo(ptX, ptY) else ellipsePath.lineTo(ptX, ptY)
                }
                ellipsePath.close()

                // Matches osm MapView ellipse styling
                drawPath(ellipsePath, color = Color(0x25D97706), style = Fill)
                drawPath(ellipsePath, color = Color(0x88D97706), style = Stroke(width = 2.dp.toPx()))

                // Label: est. σ <uncertaintyM> m (R-A: no drift or grade label)
                val labelText = "est. σ %.1f m".format(telemetry.uncertaintyM)
                val textLayout = textMeasurer.measure(
                    text = labelText,
                    style = TextStyle(fontSize = 11.sp, color = palette.textSecondary)
                )
                drawText(
                    textLayoutResult = textLayout,
                    topLeft = Offset(vehPos.x - textLayout.size.width / 2f, lowestY + 6.dp.toPx())
                )
            }

            // 10. Vehicle Chevron Puck at bottom-centre (rotated by 0 in body frame)
            // Soft drop shadow
            drawCircle(
                color = Color.Black.copy(alpha = 0.40f),
                radius = 12.dp.toPx(),
                center = Offset(vehPos.x, vehPos.y + 1.5.dp.toPx())
            )
            // Crisp white border ring
            drawCircle(
                color = Color.White,
                radius = 10.5.dp.toPx(),
                center = Offset(vehPos.x, vehPos.y)
            )
            // Vibrant IDR Blue core puck
            drawCircle(
                color = Color(0xFF008CFF),
                radius = 8.dp.toPx(),
                center = Offset(vehPos.x, vehPos.y)
            )
            // Forward precision directional chevron (0 deg, pointing straight into tunnel)
            val chevronPath = Path().apply {
                val tipY = vehPos.y - 7.dp.toPx()
                val baseY = vehPos.y - 1.5.dp.toPx()
                val halfW = 4.dp.toPx()
                moveTo(vehPos.x, tipY)
                lineTo(vehPos.x + halfW, baseY)
                lineTo(vehPos.x, baseY - 1.2.dp.toPx())
                lineTo(vehPos.x - halfW, baseY)
                close()
            }
            drawPath(chevronPath, color = Color.White, style = Fill)
        }
    }
}

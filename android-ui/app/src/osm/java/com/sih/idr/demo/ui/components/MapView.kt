package com.sih.idr.demo.ui.components

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.ColorMatrix
import android.graphics.ColorMatrixColorFilter
import android.graphics.Paint
import android.graphics.Path
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import android.view.MotionEvent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Remove
import androidx.compose.material3.Icon
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.errorEllipse
import com.sih.idr.demo.backend.routing.NavigationRoute
import com.sih.idr.demo.backend.tunnel.TunnelState
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.LocalIsDarkTheme
import com.sih.idr.demo.ui.glassmorphic
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView as OsmMapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * The `osm` flavour's map canvas (D-117, D-121): OpenStreetMap raster tiles through OSMDroid, with
 * Course-Up / North-Up, a night-vision tile filter, auto-follow with a "Re-center" pill, the track
 * and the estimator's 1 sigma error ellipse. It needs no account and no token, which is why it is
 * the flavour CI always builds; the `mapbox` flavour is the navigation UI the plan is built on.
 */
@Composable
fun MapView(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier,
    courseUpMode: Boolean = false,
    onToggleCourseUp: () -> Unit = {},
    /** Height of whatever the screen stacks over the bottom of the map; the Re-center pill clears it. */
    bottomInset: Dp = 0.dp
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val isDark = LocalIsDarkTheme.current

    var mapViewInstance by remember { mutableStateOf<OsmMapView?>(null) }
    var followVehicle by remember { mutableStateOf(true) }

    // Google Maps-style navigation smoother (continuous camera glide, lookahead, heading dampening)
    val smoother = remember {
        object {
            var isInitialized = false
            var smoothedCamLat = 0.0
            var smoothedCamLon = 0.0
            var smoothedHeadingDeg = 0f
        }
    }

    // Render cache to eliminate 30 Hz heap churn, tile flashing, and micro-stutter tearing
    val renderCache = remember {
        object {
            var lastDarkFilter: Boolean? = null
            var lastActiveRoute: NavigationRoute? = null
            var lastPathSize: Int = -1
            var cachedPathPoints: ArrayList<GeoPoint> = ArrayList()
            var lastRenderedLat = 0.0
            var lastRenderedLon = 0.0
            var lastRenderedHeading = -999f
        }
    }

    // Night Mode Color Filter for OSM Tiles (Google Maps Night Mode look)
    val nightFilter = remember {
        val cm = ColorMatrix(floatArrayOf(
            -0.82f,  0.00f,  0.00f, 0.0f, 220f,
             0.00f, -0.82f,  0.00f, 0.0f, 220f,
             0.00f,  0.00f, -0.70f, 0.0f, 238f,
             0.00f,  0.00f,  0.00f, 1.0f,   0f
        ))
        ColorMatrixColorFilter(cm)
    }

    // Retain overlay objects across recompositions
    val polyline = remember {
        Polyline().apply {
            val density = context.resources.displayMetrics.density
            outlinePaint.strokeWidth = 6f * density
            outlinePaint.strokeCap = Paint.Cap.ROUND
            outlinePaint.strokeJoin = Paint.Join.ROUND
        }
    }

    val routePolyline = remember {
        Polyline().apply {
            val density = context.resources.displayMetrics.density
            outlinePaint.strokeWidth = 7f * density
            outlinePaint.strokeCap = Paint.Cap.ROUND
            outlinePaint.strokeJoin = Paint.Join.ROUND
        }
    }

    val destMarker = remember {
        Marker(OsmMapView(context)).apply {
            icon = getDestinationIcon(context)
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
            infoWindow = null
        }
    }

    val uncertaintyPolygon = remember {
        Polygon().apply {
            val density = context.resources.displayMetrics.density
            outlinePaint.strokeWidth = 2f * density
        }
    }

    val vehicleMarker = remember {
        Marker(OsmMapView(context)).apply {
            icon = getVehicleIcon(context)
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
            infoWindow = null
        }
    }

    // Lifecycle binding for OSMDroid tile caching
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> mapViewInstance?.onResume()
                Lifecycle.Event.ON_PAUSE -> mapViewInstance?.onPause()
                else -> {}
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            mapViewInstance?.onDetach()
        }
    }

    Box(modifier = modifier.fillMaxSize()) {
        // ── Native OSMDroid MapView Embedded in Compose ──────────────
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                Configuration.getInstance().load(ctx, ctx.getSharedPreferences("osmdroid", Context.MODE_PRIVATE))
                Configuration.getInstance().userAgentValue = ctx.packageName

                OsmMapView(ctx).apply {
                    setTileSource(TileSourceFactory.MAPNIK)
                    setMultiTouchControls(true)
                    zoomController.setVisibility(org.osmdroid.views.CustomZoomButtonsController.Visibility.NEVER)
                    isTilesScaledToDpi = true
                    controller.setZoom(18.0)
                    controller.setCenter(GeoPoint(telemetry.latitude, telemetry.longitude))

                    // Detect manual drag to pause auto-follow without fighting user
                    setOnTouchListener { _, event ->
                        if (event.action == MotionEvent.ACTION_MOVE) {
                            followVehicle = false
                        }
                        false
                    }

                    // Add overlays in back-to-front order
                    overlays.add(routePolyline)
                    overlays.add(destMarker)
                    overlays.add(uncertaintyPolygon)
                    overlays.add(polyline)
                    overlays.add(vehicleMarker)

                    mapViewInstance = this
                }
            },
            update = { osmView ->
                val currentPoint = GeoPoint(telemetry.latitude, telemetry.longitude)
                val rawHeadingDeg = Math.toDegrees(telemetry.yawRad.toDouble()).toFloat()
                val speedMps = telemetry.speedMps
                val isMoving = speedMps >= 0.35f // ~1.26 km/h threshold

                // 1. Heading Smoothing with Stationary Deadband & Shortest-Arc Interpolation
                val diff = ((rawHeadingDeg - smoother.smoothedHeadingDeg + 180f) % 360f + 360f) % 360f - 180f
                if (!smoother.isInitialized) {
                    smoother.smoothedHeadingDeg = rawHeadingDeg
                } else if (isMoving || abs(diff) > 45f) {
                    val alpha = if (isMoving) 0.18f else 0.08f
                    smoother.smoothedHeadingDeg = (smoother.smoothedHeadingDeg + diff * alpha) % 360f
                    if (smoother.smoothedHeadingDeg < 0f) smoother.smoothedHeadingDeg += 360f
                }
                val effectiveHeading = smoother.smoothedHeadingDeg

                // 2. Dark/Night mode tile filter (cached to eliminate tile flickering)
                if (renderCache.lastDarkFilter != isDark) {
                    renderCache.lastDarkFilter = isDark
                    osmView.overlayManager.tilesOverlay.setColorFilter(if (isDark) nightFilter else null)
                }

                // 3. Camera Orientation: Course-Up vs North-Up
                if (courseUpMode) {
                    if (osmView.mapOrientation != -effectiveHeading) {
                        osmView.mapOrientation = -effectiveHeading
                    }
                    vehicleMarker.rotation = 0f // Straight ahead in course-up
                } else {
                    if (osmView.mapOrientation != 0f) {
                        osmView.mapOrientation = 0f
                    }
                    vehicleMarker.rotation = effectiveHeading // Rotates relative to north
                }

                // 4. Update vehicle position
                vehicleMarker.position = currentPoint

                // 5. Update the 1 sigma error ellipse from the reported covariance (D-125). For the
                //    demo estimator it is a circle, because that estimator carries one scalar.
                if (telemetry.running && telemetry.uncertaintyM > 0f) {
                    uncertaintyPolygon.points = ellipseGeoPoints(telemetry)
                    val inTunnelOrHighUncertainty = telemetry.tunnelModeActive || telemetry.uncertaintyM > 25f
                    val targetFill = if (inTunnelOrHighUncertainty) 0x25D97706.toInt() else if (isDark) 0x2510B981.toInt() else 0x1A16A34A.toInt()
                    val targetOutline = if (inTunnelOrHighUncertainty) 0x88D97706.toInt() else if (isDark) 0x8810B981.toInt() else 0x8816A34A.toInt()
                    if (uncertaintyPolygon.fillPaint.color != targetFill) uncertaintyPolygon.fillPaint.color = targetFill
                    if (uncertaintyPolygon.outlinePaint.color != targetOutline) uncertaintyPolygon.outlinePaint.color = targetOutline
                } else if (uncertaintyPolygon.points.isNotEmpty()) {
                    uncertaintyPolygon.points = ArrayList()
                }

                // 6. Update trajectory path (buffered to avoid 30 Hz heap churn)
                val latPerMetre = 1.0 / 111_320.0
                val lonPerMetre = 1.0 / (111_320.0 * cos(Math.toRadians(telemetry.originLat)))
                val oLat = telemetry.originLat
                val oLon = telemetry.originLon

                if (telemetry.running && (telemetry.path.isNotEmpty() || telemetry.totalDistanceM > 0f)) {
                    if (telemetry.path.size != renderCache.lastPathSize) {
                        renderCache.lastPathSize = telemetry.path.size
                        val pathPoints = ArrayList<GeoPoint>(telemetry.path.size + 1)
                        for (p in telemetry.path) {
                            pathPoints.add(GeoPoint(oLat + p.northM * latPerMetre, oLon + p.eastM * lonPerMetre))
                        }
                        pathPoints.add(currentPoint)
                        renderCache.cachedPathPoints = pathPoints
                        polyline.setPoints(pathPoints)
                    } else if (renderCache.cachedPathPoints.isNotEmpty()) {
                        renderCache.cachedPathPoints[renderCache.cachedPathPoints.size - 1] = currentPoint
                        polyline.setPoints(renderCache.cachedPathPoints)
                    }
                } else if (renderCache.lastPathSize != 0) {
                    renderCache.lastPathSize = 0
                    renderCache.cachedPathPoints.clear()
                    polyline.setPoints(ArrayList())
                }
                val targetTrackColor = if (isDark) {
                    android.graphics.Color.parseColor("#38BDF8")
                } else {
                    android.graphics.Color.parseColor("#2563EB")
                }
                if (polyline.outlinePaint.color != targetTrackColor) {
                    polyline.outlinePaint.color = targetTrackColor
                }

                // 6b. Update active route polyline and destination marker (cached on route change)
                val activeRoute = telemetry.activeRoute
                if (activeRoute !== renderCache.lastActiveRoute) {
                    renderCache.lastActiveRoute = activeRoute
                    if (activeRoute != null && activeRoute.points.isNotEmpty()) {
                        val rPoints = ArrayList<GeoPoint>(activeRoute.points.size)
                        for (p in activeRoute.points) {
                            rPoints.add(GeoPoint(p.latitude, p.longitude))
                        }
                        routePolyline.setPoints(rPoints)
                        destMarker.position = GeoPoint(activeRoute.destinationCoord.latitude, activeRoute.destinationCoord.longitude)
                        destMarker.isEnabled = true
                    } else {
                        routePolyline.setPoints(ArrayList())
                        destMarker.isEnabled = false
                    }
                }

                if (activeRoute != null) {
                    val inTunnel = telemetry.tunnelState == TunnelState.TUNNEL_ACTIVE_IDR || telemetry.tunnelModeActive
                    val targetRouteColor = if (inTunnel) {
                        android.graphics.Color.parseColor("#00E5FF")
                    } else if (isDark) {
                        android.graphics.Color.parseColor("#38BDF8")
                    } else {
                        android.graphics.Color.parseColor("#008CFF")
                    }
                    if (routePolyline.outlinePaint.color != targetRouteColor) {
                        routePolyline.outlinePaint.color = targetRouteColor
                    }
                }

                // 7. Navigation Lookahead Lead & Continuous Camera Gliding (Google Maps style)
                val hasValidPos = (telemetry.latitude != 0.0 || telemetry.longitude != 0.0)
                if (hasValidPos) {
                    val lookaheadM = if (courseUpMode && isMoving) {
                        (speedMps * 2.2f).coerceIn(15f, 60f)
                    } else {
                        0f
                    }
                    val headingRad = Math.toRadians(effectiveHeading.toDouble())
                    val targetCamLat = telemetry.latitude + lookaheadM * cos(headingRad) * latPerMetre
                    val targetCamLon = telemetry.longitude + lookaheadM * sin(headingRad) * lonPerMetre

                    if (followVehicle) {
                        val dLat = targetCamLat - smoother.smoothedCamLat
                        val dLon = targetCamLon - smoother.smoothedCamLon
                        val dLatM = dLat * 111_320.0
                        val dLonM = dLon * 111_320.0 * cos(Math.toRadians(targetCamLat))
                        val distM = sqrt(dLatM * dLatM + dLonM * dLonM)

                        if (!smoother.isInitialized || distM > 80.0) {
                            smoother.smoothedCamLat = targetCamLat
                            smoother.smoothedCamLon = targetCamLon
                            smoother.isInitialized = true
                        } else {
                            val posAlpha = 0.22f
                            smoother.smoothedCamLat += dLat * posAlpha
                            smoother.smoothedCamLon += dLon * posAlpha
                        }

                        osmView.controller.setCenter(GeoPoint(smoother.smoothedCamLat, smoother.smoothedCamLon))
                    } else {
                        smoother.smoothedCamLat = targetCamLat
                        smoother.smoothedCamLon = targetCamLon
                    }
                }

                // 8. Differential invalidation: only redraw canvas when delta is visually meaningful
                val dRenderLat = abs(telemetry.latitude - renderCache.lastRenderedLat)
                val dRenderLon = abs(telemetry.longitude - renderCache.lastRenderedLon)
                val dRenderHeading = abs(effectiveHeading - renderCache.lastRenderedHeading)
                if (dRenderLat > 0.0000005 || dRenderLon > 0.0000005 || dRenderHeading > 0.2f) {
                    osmView.invalidate()
                    renderCache.lastRenderedLat = telemetry.latitude
                    renderCache.lastRenderedLon = telemetry.longitude
                    renderCache.lastRenderedHeading = effectiveHeading
                }
            }
        )

        // ── Floating Zoom Capsule (Apple Maps / Tesla style) ──
        ZoomCapsule(
            onZoomIn = { mapViewInstance?.controller?.zoomIn() },
            onZoomOut = { mapViewInstance?.controller?.zoomOut() },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 16.dp, bottom = bottomInset + 16.dp)
        )

        // ── Google Maps Floating "Re-center" Button (Cleanly floating above bottom sheet) ──
        AnimatedVisibility(
            visible = !followVehicle,
            enter = fadeIn() + slideInVertically { it / 2 },
            exit = fadeOut() + slideOutVertically { it / 2 },
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = bottomInset + 16.dp)
        ) {
            RecenterPill(onClick = {
                followVehicle = true
                smoother.smoothedCamLat = telemetry.latitude
                smoother.smoothedCamLon = telemetry.longitude
                val currentPoint = GeoPoint(telemetry.latitude, telemetry.longitude)
                mapViewInstance?.controller?.animateTo(currentPoint)
                mapViewInstance?.controller?.setZoom(18.0)
            })
        }
    }
}

/** The 1 sigma ellipse of the reported covariance as WGS84 points around the current position. */
private fun ellipseGeoPoints(telemetry: TelemetryState): ArrayList<GeoPoint> {
    val ellipse = errorEllipse(telemetry.covNorthM2, telemetry.covNorthEastM2, telemetry.covEastM2)
    val lat = telemetry.latitude
    val lon = telemetry.longitude
    val latPerM = 1.0 / 111_320.0
    val lonPerM = 1.0 / (111_320.0 * cos(Math.toRadians(lat)))
    val outline = ellipse.outline()
    val points = ArrayList<GeoPoint>(outline.size)
    for (p in outline) {
        points.add(GeoPoint(lat + p.northM * latPerM, lon + p.eastM * lonPerM))
    }
    return points
}

/**
 * Compact, seamless navigation puck with subtle drop shadow, crisp white ring,
 * and precision forward directional chevron (Google/Apple Maps style).
 */
private fun getVehicleIcon(context: Context): Drawable {
    val density = context.resources.displayMetrics.density
    val sizePx = (26 * density).roundToInt()
    val center = sizePx / 2f
    val bitmap = Bitmap.createBitmap(sizePx, sizePx, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)

    // 1. Soft subtle drop shadow
    val shadowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.argb(55, 0, 0, 0)
    }
    canvas.drawCircle(center, center + (1f * density), 11.5f * density, shadowPaint)

    // 2. Crisp outer white border
    val whitePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.WHITE
    }
    canvas.drawCircle(center, center, 10.5f * density, whitePaint)

    // 3. Vibrant IDR Blue core puck
    val bluePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.parseColor("#008CFF")
    }
    canvas.drawCircle(center, center, 8f * density, bluePaint)

    // 4. Sharp precision directional chevron pointing forward (0°)
    val chevronPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.WHITE
        style = Paint.Style.FILL
    }
    val chevron = Path().apply {
        val tipY = center - 9f * density
        val baseY = center - 3f * density
        val halfW = 4.5f * density
        moveTo(center, tipY)
        lineTo(center + halfW, baseY)
        lineTo(center, baseY - 1.5f * density)
        lineTo(center - halfW, baseY)
        close()
    }
    canvas.drawPath(chevron, chevronPaint)

    return BitmapDrawable(context.resources, bitmap)
}

private fun getDestinationIcon(context: Context): Drawable {
    val density = context.resources.displayMetrics.density
    val sizePx = (32 * density).roundToInt()
    val center = sizePx / 2f
    val bitmap = Bitmap.createBitmap(sizePx, sizePx, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    // Red pin head
    paint.color = android.graphics.Color.parseColor("#EF4444")
    canvas.drawCircle(center, sizePx * 0.38f, sizePx * 0.32f, paint)

    // Pin point stem
    val path = Path().apply {
        moveTo(sizePx * 0.22f, sizePx * 0.44f)
        lineTo(center, sizePx * 0.95f)
        lineTo(sizePx * 0.78f, sizePx * 0.44f)
        close()
    }
    canvas.drawPath(path, paint)

    // White inner dot
    paint.color = android.graphics.Color.WHITE
    canvas.drawCircle(center, sizePx * 0.38f, sizePx * 0.12f, paint)

    return BitmapDrawable(context.resources, bitmap)
}


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
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.errorEllipse
import com.sih.idr.demo.ui.LocalIsDarkTheme
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView as OsmMapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline
import kotlin.math.cos
import kotlin.math.roundToInt

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
    onToggleCourseUp: () -> Unit = {}
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val isDark = LocalIsDarkTheme.current

    var mapViewInstance by remember { mutableStateOf<OsmMapView?>(null) }
    var followVehicle by remember { mutableStateOf(true) }

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
                    overlays.add(uncertaintyPolygon)
                    overlays.add(polyline)
                    overlays.add(vehicleMarker)

                    mapViewInstance = this
                }
            },
            update = { osmView ->
                val currentPoint = GeoPoint(telemetry.latitude, telemetry.longitude)
                val headingDeg = Math.toDegrees(telemetry.yawRad.toDouble()).toFloat()

                // 1. Dark/Night mode tile filter
                osmView.overlayManager.tilesOverlay.setColorFilter(if (isDark) nightFilter else null)

                // 2. Camera Orientation: Course-Up vs North-Up
                if (courseUpMode) {
                    osmView.mapOrientation = -headingDeg
                    vehicleMarker.rotation = 0f // Straight ahead in course-up
                } else {
                    osmView.mapOrientation = 0f
                    vehicleMarker.rotation = headingDeg // Rotates relative to north
                }

                // 3. Update vehicle position
                vehicleMarker.position = currentPoint

                // 4. Update the 1 sigma error ellipse from the reported covariance (D-125). For the
                //    demo estimator it is a circle, because that estimator carries one scalar.
                if (telemetry.running && telemetry.uncertaintyM > 0f) {
                    uncertaintyPolygon.points = ellipseGeoPoints(telemetry)
                    if (telemetry.tunnelModeActive || telemetry.uncertaintyM > 25f) {
                        uncertaintyPolygon.fillPaint.color = 0x25D97706.toInt() // Amber fill
                        uncertaintyPolygon.outlinePaint.color = 0x88D97706.toInt() // Amber stroke
                    } else {
                        uncertaintyPolygon.fillPaint.color = if (isDark) 0x2510B981.toInt() else 0x1A16A34A.toInt()
                        uncertaintyPolygon.outlinePaint.color = if (isDark) 0x8810B981.toInt() else 0x8816A34A.toInt()
                    }
                } else {
                    uncertaintyPolygon.points = ArrayList()
                }

                // 5. Update trajectory path
                val latPerMetre = 1.0 / 111_320.0
                val lonPerMetre = 1.0 / (111_320.0 * cos(Math.toRadians(telemetry.originLat)))
                val oLat = telemetry.originLat
                val oLon = telemetry.originLon

                if (telemetry.running && (telemetry.path.isNotEmpty() || telemetry.totalDistanceM > 0f)) {
                    val pathPoints = ArrayList<GeoPoint>(telemetry.path.size + 1)
                    for (p in telemetry.path) {
                        pathPoints.add(GeoPoint(oLat + p.northM * latPerMetre, oLon + p.eastM * lonPerMetre))
                    }
                    pathPoints.add(currentPoint)
                    polyline.setPoints(pathPoints)
                } else {
                    polyline.setPoints(ArrayList())
                }
                polyline.outlinePaint.color = if (isDark) {
                    android.graphics.Color.parseColor("#38BDF8")
                } else {
                    android.graphics.Color.parseColor("#2563EB")
                }

                // 6. Camera follow
                if (followVehicle) {
                    osmView.controller.setCenter(currentPoint)
                }

                osmView.invalidate()
            }
        )

        // ── Floating Zoom Controls (Comfortably centered on right edge) ──
        Column(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .padding(end = 16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Zoom In Button (+)
            MapControlButton(icon = Icons.Rounded.Add, contentDescription = "Zoom In") {
                mapViewInstance?.controller?.zoomIn()
            }

            // Zoom Out Button (−)
            MapControlButton(icon = Icons.Rounded.Remove, contentDescription = "Zoom Out") {
                mapViewInstance?.controller?.zoomOut()
            }
        }

        // ── Google Maps Floating "Re-center" Button (Cleanly floating above bottom sheet) ──
        AnimatedVisibility(
            visible = !followVehicle,
            enter = fadeIn() + slideInVertically { it / 2 },
            exit = fadeOut() + slideOutVertically { it / 2 },
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 360.dp)
        ) {
            RecenterPill(onClick = {
                followVehicle = true
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

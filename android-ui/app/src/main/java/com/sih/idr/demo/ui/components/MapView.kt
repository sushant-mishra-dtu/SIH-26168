package com.sih.idr.demo.ui.components

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import android.view.MotionEvent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.MyLocation
import androidx.compose.material.icons.rounded.Remove
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.ui.IDRColors
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView as OsmMapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin

/**
 * Online map canvas streaming OpenStreetMap tiles with pinch-to-zoom, drag-to-pan,
 * on-screen zoom buttons, seamless vehicle pointer, and dead-reckoning trajectory overlay.
 */
@Composable
fun MapView(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    var mapViewInstance by remember { mutableStateOf<OsmMapView?>(null) }
    var followVehicle by remember { mutableStateOf(true) }

    // Retain overlay objects across recompositions
    val polyline = remember {
        Polyline().apply {
            val density = context.resources.displayMetrics.density
            outlinePaint.color = android.graphics.Color.parseColor("#2563EB")
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

                // 1. Update vehicle position and heading rotation
                vehicleMarker.position = currentPoint
                vehicleMarker.rotation = Math.toDegrees(telemetry.yawRad.toDouble()).toFloat()

                // 2. Update uncertainty circle (radius in metres)
                if (telemetry.running && telemetry.uncertaintyM > 0f) {
                    val circlePoints = generateCirclePoints(currentPoint, telemetry.uncertaintyM.toDouble())
                    uncertaintyPolygon.points = circlePoints
                    if (telemetry.tunnelModeActive || telemetry.uncertaintyM > 25f) {
                        uncertaintyPolygon.fillPaint.color = 0x22D97706.toInt() // Amber fill
                        uncertaintyPolygon.outlinePaint.color = 0x88D97706.toInt() // Amber stroke
                    } else {
                        uncertaintyPolygon.fillPaint.color = 0x1A16A34A.toInt() // Green fill
                        uncertaintyPolygon.outlinePaint.color = 0x8816A34A.toInt() // Green stroke
                    }
                } else {
                    uncertaintyPolygon.points = ArrayList()
                }

                // 3. Update trajectory path
                val latPerMetre = 1.0 / 111_320.0
                val lonPerMetre = 1.0 / (111_320.0 * cos(Math.toRadians(telemetry.originLat)))
                val oLat = telemetry.originLat
                val oLon = telemetry.originLon

                val pathPoints = ArrayList<GeoPoint>(telemetry.path.size + 1)
                for (p in telemetry.path) {
                    pathPoints.add(GeoPoint(oLat + p.northM * latPerMetre, oLon + p.eastM * lonPerMetre))
                }
                pathPoints.add(currentPoint)
                polyline.setPoints(pathPoints)

                // 4. Locked camera follow (using setCenter directly avoids animation jitter)
                if (followVehicle) {
                    osmView.controller.setCenter(currentPoint)
                }

                osmView.invalidate()
            }
        )

        // ── Subtitle / Mode Disclaimer ──────────────────────────────
        Surface(
            color = IDRColors.OverlayBg,
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier
                .align(Alignment.TopCenter)
                .statusBarsPadding()
                .padding(top = 72.dp)
                .shadow(4.dp, RoundedCornerShape(16.dp), spotColor = IDRColors.TextDim)
        ) {
            Text(
                text = "OpenStreetMap • Live Online Tile Stream",
                style = MaterialTheme.typography.bodySmall,
                color = IDRColors.TextSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp)
            )
        }

        // ── Floating Zoom & Re-Center Controls ──────────────────────
        Column(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .statusBarsPadding()
                .padding(top = 112.dp, end = 16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Zoom In Button (+)
            MapControlButton(icon = Icons.Rounded.Add) {
                mapViewInstance?.controller?.zoomIn()
            }

            // Zoom Out Button (−)
            MapControlButton(icon = Icons.Rounded.Remove) {
                mapViewInstance?.controller?.zoomOut()
            }

            // Re-center / Follow Vehicle Button (smoothly glides camera back to vehicle)
            MapControlButton(
                icon = Icons.Rounded.MyLocation,
                active = !followVehicle
            ) {
                followVehicle = true
                val currentPoint = GeoPoint(telemetry.latitude, telemetry.longitude)
                mapViewInstance?.controller?.animateTo(currentPoint)
                mapViewInstance?.controller?.setZoom(18.0)
            }
        }
    }
}

@Composable
private fun MapControlButton(
    icon: ImageVector,
    active: Boolean = false,
    onClick: () -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    Surface(
        color = if (active) IDRColors.Blue.copy(alpha = 0.2f) else IDRColors.BgPrimary,
        shape = CircleShape,
        modifier = Modifier
            .size(44.dp)
            .scale(if (isPressed) 0.88f else 1f)
            .shadow(6.dp, CircleShape, spotColor = IDRColors.TextDim)
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
    ) {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (active) IDRColors.Blue else IDRColors.TextPrimary,
                modifier = Modifier.size(22.dp)
            )
        }
    }
}

/** Generates circle points in WGS84 coordinates given center and radius in metres. */
private fun generateCirclePoints(center: GeoPoint, radiusMeters: Double, count: Int = 36): ArrayList<GeoPoint> {
    val points = ArrayList<GeoPoint>(count)
    val lat = center.latitude
    val lon = center.longitude
    val latPerM = 1.0 / 111_320.0
    val lonPerM = 1.0 / (111_320.0 * cos(Math.toRadians(lat)))
    for (i in 0 until count) {
        val angle = 2.0 * Math.PI * i / count
        val dLat = radiusMeters * cos(angle) * latPerM
        val dLon = radiusMeters * sin(angle) * lonPerM
        points.add(GeoPoint(lat + dLat, lon + dLon))
    }
    return points
}

/**
 * Compact, seamless navigation puck with subtle drop shadow, crisp white ring,
 * and precision forward directional chevron (Google/Apple Maps style).
 */
private fun getVehicleIcon(context: Context): Drawable {
    val density = context.resources.displayMetrics.density
    // Compact 24dp size: sleek, precise, seamless
    val sizePx = (24 * density).roundToInt()
    val center = sizePx / 2f
    val bitmap = Bitmap.createBitmap(sizePx, sizePx, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)

    // 1. Soft subtle drop shadow
    val shadowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.argb(45, 0, 0, 0)
    }
    canvas.drawCircle(center, center + (1f * density), 10.5f * density, shadowPaint)

    // 2. Crisp outer white border
    val whitePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.WHITE
    }
    canvas.drawCircle(center, center, 9.5f * density, whitePaint)

    // 3. Vibrant IDR Blue core puck
    val bluePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.parseColor("#2563EB")
    }
    canvas.drawCircle(center, center, 7f * density, bluePaint)

    // 4. Sharp precision directional chevron at the top pointing North (0°)
    val chevronPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = android.graphics.Color.WHITE
        style = Paint.Style.FILL
    }
    val chevron = Path().apply {
        val tipY = center - 8f * density
        val baseY = center - 2.5f * density
        val halfW = 4f * density
        moveTo(center, tipY)
        lineTo(center + halfW, baseY)
        lineTo(center, baseY - 1.5f * density)
        lineTo(center - halfW, baseY)
        close()
    }
    canvas.drawPath(chevron, chevronPaint)

    return BitmapDrawable(context.resources, bitmap)
}

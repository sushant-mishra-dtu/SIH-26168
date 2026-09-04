package com.sih.idr.demo.ui.components

import android.content.Context
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.ui.IDRColors
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView as OsmMapView
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline

private val DEFAULT_ORIGIN = GeoPoint(28.6129, 77.2295)

@Composable
fun MapView(
    telemetry: TelemetryState,
    origin: GeoPoint = DEFAULT_ORIGIN,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current

    // Initialize osmdroid config once
    LaunchedEffect(Unit) {
        Configuration.getInstance().userAgentValue = context.packageName
    }

    val currentPoint = nedToGeoPoint(
        origin,
        telemetry.positionNorthM.toDouble(),
        telemetry.positionEastM.toDouble()
    )
    
    // We only create the map once, then update it via update block
    AndroidView(
        modifier = modifier.fillMaxSize(),
        factory = { ctx ->
            OsmMapView(ctx).apply {
                val cartoDbPositron = org.osmdroid.tileprovider.tilesource.XYTileSource(
                    "CartoDB Positron",
                    0, 20, 256, ".png",
                    arrayOf(
                        "https://a.basemaps.cartocdn.com/light_all/",
                        "https://b.basemaps.cartocdn.com/light_all/",
                        "https://c.basemaps.cartocdn.com/light_all/",
                        "https://d.basemaps.cartocdn.com/light_all/"
                    ),
                    "© OpenStreetMap contributors, © CARTO"
                )
                setTileSource(cartoDbPositron)
                setMultiTouchControls(true)
                isTilesScaledToDpi = true
                
                controller.setZoom(17.5)
                controller.setCenter(currentPoint)
            }
        },
        update = { map ->
            // Smoothly move camera
            map.controller.animateTo(currentPoint)
            
            // Clear previous overlays
            map.overlays.clear()
            
            // Draw Route
            val routePoints = telemetry.path.takeLast(300).map { tp ->
                nedToGeoPoint(origin, tp.northM.toDouble(), tp.eastM.toDouble())
            }
            if (routePoints.size > 1) {
                val polyline = Polyline(map).apply {
                    setPoints(routePoints)
                    outlinePaint.color = IDRColors.Blue.toArgb()
                    outlinePaint.strokeWidth = 14f
                    outlinePaint.strokeCap = android.graphics.Paint.Cap.ROUND
                    outlinePaint.strokeJoin = android.graphics.Paint.Join.ROUND
                }
                map.overlays.add(polyline)
            }

            // Draw Uncertainty Circle (Polygon approximating a circle)
            val radiusM = telemetry.uncertaintyM.toDouble().coerceAtLeast(5.0)
            val circleColor = when {
                telemetry.uncertaintyM < 15f -> IDRColors.GreenOk
                telemetry.uncertaintyM < 40f -> IDRColors.AmberWarn
                else -> IDRColors.RedError
            }
            val circle = Polygon.pointsAsCircle(currentPoint, radiusM).let { points ->
                Polygon(map).apply {
                    setPoints(points)
                    fillPaint.color = circleColor.copy(alpha = 0.12f).toArgb()
                    outlinePaint.color = circleColor.copy(alpha = 0.5f).toArgb()
                    outlinePaint.strokeWidth = 4f
                }
            }
            map.overlays.add(circle)
            
            // Draw marker
            val marker = Marker(map).apply {
                position = currentPoint
                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER)
                // Use a default Android icon for the car/dot, or a custom one if available
                icon = context.getDrawable(android.R.drawable.presence_online) 
            }
            map.overlays.add(marker)
            
            map.invalidate()
        }
    )
}

private fun nedToGeoPoint(origin: GeoPoint, northM: Double, eastM: Double): GeoPoint {
    val latPerMetre = 1.0 / 111_320.0
    val lonPerMetre = 1.0 / (111_320.0 * Math.cos(Math.toRadians(origin.latitude)))
    return GeoPoint(
        origin.latitude + northM * latPerMetre,
        origin.longitude + eastM * lonPerMetre
    )
}

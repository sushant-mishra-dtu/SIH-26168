package com.sih.idr.demo.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Remove
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.mapbox.android.gestures.MoveGestureDetector
import com.mapbox.geojson.Point
import com.mapbox.maps.CameraOptions
import com.mapbox.maps.extension.compose.MapEffect
import com.mapbox.maps.extension.compose.MapboxMap
import com.mapbox.maps.extension.compose.animation.viewport.rememberMapViewportState
import com.mapbox.maps.extension.compose.annotation.generated.CircleAnnotation
import com.mapbox.maps.extension.compose.annotation.generated.PolygonAnnotation
import com.mapbox.maps.extension.compose.annotation.generated.PolylineAnnotation
import com.mapbox.maps.extension.compose.style.MapStyle
import com.mapbox.maps.plugin.animation.MapAnimationOptions
import com.mapbox.maps.plugin.gestures.OnMapLongClickListener
import com.mapbox.maps.plugin.gestures.OnMoveListener
import com.mapbox.maps.plugin.gestures.gestures
import com.mapbox.navigation.ui.maps.NavigationStyles
import com.sih.idr.demo.R
import com.sih.idr.demo.backend.TelemetryState
import com.sih.idr.demo.backend.errorEllipse
import com.sih.idr.demo.backend.mapbox.InekfLocationProvider
import com.sih.idr.demo.ui.LocalIDRPalette
import com.sih.idr.demo.ui.LocalIsDarkTheme
import kotlin.math.cos

/**
 * The `mapbox` flavour's map canvas: the section 7.10 hello-world. It proves three things and
 * deliberately no more -- that the 3.30.1 / 11.30.1 artifacts resolve and compile under this
 * project's AGP and Kotlin, that a `MapboxMap` composable renders inside the existing screen, and
 * that the IDR-owned layer of rule R4 (`docs/UI_UX_NAVIGATION_PLAN.md` section 7.2) draws from
 * [TelemetryState] alone.
 *
 * **What is ours and what is theirs.** Everything drawn here -- the track, the 1 sigma ellipse
 * and the pose dot -- is computed from the estimator's state by us. The SDK's own location puck
 * (`NavigationLocationProvider`, snapped and smoothed by its map matcher) is not enabled yet; it
 * arrives with the trip session in the replay milestone (section 7.9), and when it does both pucks
 * stay on screen and labelled, because the pair is the only visual that proves which estimator is
 * driving.
 *
 * Camera: a plain `easeTo` per state update, one feed cadence long. `NavigationCamera` with
 * `keyPoints` replaces it in the replay milestone; for a hello-world the simple thing is right.
 */
@Composable
fun MapView(
    telemetry: TelemetryState,
    modifier: Modifier = Modifier,
    courseUpMode: Boolean = false,
    onToggleCourseUp: () -> Unit = {},
    /** Height of whatever the screen stacks over the bottom of the map; the Re-center pill clears it. */
    bottomInset: Dp = 0.dp,
    /** A long press on the map, as WGS84 latitude and longitude. */
    onMapLongPress: ((Double, Double) -> Unit)? = null
) {
    val context = LocalContext.current
    val isDark = LocalIsDarkTheme.current
    val palette = LocalIDRPalette.current

    // The public token is injected from local.properties at build time (D-122). Without one the
    // map cannot load a style; say so rather than render a blank canvas that looks like a bug.
    val hasToken = remember { context.getString(R.string.mapbox_access_token).isNotBlank() }
    if (!hasToken) {
        MissingTokenState(modifier)
        return
    }

    var followVehicle by remember { mutableStateOf(true) }
    val position = Point.fromLngLat(telemetry.longitude, telemetry.latitude)
    val headingDeg = Math.toDegrees(telemetry.yawRad.toDouble())

    val viewportState = rememberMapViewportState {
        setCameraOptions {
            center(position)
            zoom(FOLLOW_ZOOM)
        }
    }

    // Follow the pose. Keyed on the pose clock so a re-emitted identical state does not restart
    // the animation, and on the bearing mode so a toggle re-frames immediately.
    LaunchedEffect(followVehicle, telemetry.poseElapsedMs, courseUpMode) {
        if (!followVehicle || !telemetry.running) return@LaunchedEffect
        viewportState.easeTo(
            CameraOptions.Builder()
                .center(position)
                .bearing(if (courseUpMode) headingDeg else 0.0)
                .build(),
            MapAnimationOptions.Builder().duration(InekfLocationProvider.CADENCE_MS).build()
        )
    }

    Box(modifier = modifier.fillMaxSize()) {
        MapboxMap(
            modifier = Modifier.fillMaxSize(),
            mapViewportState = viewportState,
            onMapLongClickListener = onMapLongPress?.let { handler ->
                OnMapLongClickListener { point ->
                    handler(point.latitude(), point.longitude())
                    true
                }
            },
            style = {
                // Classic navigation styles for v1 (D-121); the Standard light preset is the
                // nicer theme flip but has the slot and buildings caveats of section 7.6.
                MapStyle(
                    style = if (isDark) NavigationStyles.NAVIGATION_NIGHT_STYLE
                    else NavigationStyles.NAVIGATION_DAY_STYLE
                )
            }
        ) {
            // A drag pauses auto-follow without fighting the user; the pill below restores it.
            MapEffect(Unit) { mapView ->
                mapView.gestures.addOnMoveListener(object : OnMoveListener {
                    override fun onMoveBegin(detector: MoveGestureDetector) {
                        followVehicle = false
                    }

                    override fun onMove(detector: MoveGestureDetector): Boolean = false
                    override fun onMoveEnd(detector: MoveGestureDetector) = Unit
                })
            }

            // ── IDR-owned layer (R4). Nothing here is Mapbox's estimate. ─────────────────
            if (telemetry.running && telemetry.poseElapsedMs > 0L) {
                val trackPoints = remember(telemetry.path, position) {
                    telemetry.path.map { p ->
                        Point.fromLngLat(
                            telemetry.originLon + p.eastM * lonPerMetre(telemetry.originLat),
                            telemetry.originLat + p.northM * LAT_PER_METRE
                        )
                    } + position
                }
                if (trackPoints.size >= 2) {
                    PolylineAnnotation(points = trackPoints) {
                        lineColor = if (isDark) Color(0xFF38BDF8) else Color(0xFF2563EB)
                        lineWidth = 5.0
                    }
                }

                // 1 sigma ellipse of the reported covariance (D-125). Amber while dead reckoning
                // or once it has grown past 25 m; the palette's OK green while a fix is fresh.
                val ellipseRing = remember(
                    telemetry.covNorthM2, telemetry.covNorthEastM2, telemetry.covEastM2, position
                ) {
                    val ellipse = errorEllipse(
                        telemetry.covNorthM2, telemetry.covNorthEastM2, telemetry.covEastM2
                    )
                    val lonPerM = lonPerMetre(telemetry.latitude)
                    val ring = ellipse.outline().map { p ->
                        Point.fromLngLat(
                            telemetry.longitude + p.eastM * lonPerM,
                            telemetry.latitude + p.northM * LAT_PER_METRE
                        )
                    }
                    listOf(ring + ring.first())
                }
                val coasting = telemetry.tunnelModeActive || telemetry.uncertaintyM > 25f
                PolygonAnnotation(points = ellipseRing) {
                    fillColor = if (coasting) Color(0xFFD97706) else palette.statusOk
                    fillOpacity = 0.18
                    fillOutlineColor = if (coasting) Color(0xFFD97706) else palette.statusOk
                }

                // Raw pose. A dot, not a chevron, on purpose: the chevron is what the SDK's puck
                // will be, and the two must not be confused in a screenshot.
                CircleAnnotation(point = position) {
                    circleRadius = 7.0
                    circleColor = palette.primary
                    circleStrokeColor = Color.White
                    circleStrokeWidth = 2.5
                }
            }
        }

        // ── Floating zoom controls (shared chrome) ──
        ZoomCapsule(
            onZoomIn = {
                val zoom = viewportState.cameraState?.zoom ?: FOLLOW_ZOOM
                viewportState.easeTo(CameraOptions.Builder().zoom(zoom + 1.0).build())
            },
            onZoomOut = {
                val zoom = viewportState.cameraState?.zoom ?: FOLLOW_ZOOM
                viewportState.easeTo(CameraOptions.Builder().zoom(zoom - 1.0).build())
            },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(end = 16.dp, bottom = bottomInset + 16.dp)
        )

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
                viewportState.easeTo(
                    CameraOptions.Builder().center(position).zoom(FOLLOW_ZOOM).build()
                )
            })
        }
    }
}

/** D-080: no token is an empty state that says what it is, not a blank map. */
@Composable
private fun MissingTokenState(modifier: Modifier) {
    val palette = LocalIDRPalette.current
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(palette.bgPrimary)
            .padding(32.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = "No Mapbox public token in this build.\n\n" +
                "Put MAPBOX_PUBLIC_TOKEN=<your pk token> in android-ui/local.properties and " +
                "rebuild the mapbox flavour, or build the osm flavour instead.",
            style = MaterialTheme.typography.bodyMedium,
            color = palette.textSecondary,
            textAlign = TextAlign.Center
        )
    }
}

private const val FOLLOW_ZOOM = 17.0
private const val LAT_PER_METRE = 1.0 / 111_320.0

private fun lonPerMetre(latDeg: Double): Double = 1.0 / (111_320.0 * cos(Math.toRadians(latDeg)))

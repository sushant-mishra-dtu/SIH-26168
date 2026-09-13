package com.sih.idr.demo.backend.mapbox

import android.content.Context
import com.mapbox.bindgen.ExpectedFactory
import com.mapbox.common.location.DeviceLocationProvider
import com.mapbox.common.location.DeviceLocationProviderFactory
import com.mapbox.common.location.LocationError
import com.mapbox.navigation.base.options.LocationOptions
import com.mapbox.navigation.base.options.NavigationOptions
import com.mapbox.navigation.core.lifecycle.MapboxNavigationApp

/**
 * Process-wide Navigation SDK setup (D-121, D-123). One `MapboxNavigation` per process, configured
 * once; activities `attach` to it and never destroy it (destroying ends the billed trip and restarts
 * the matcher's warm-up, `docs/UI_UX_NAVIGATION_PLAN.md` section 7.10).
 *
 * The two lines that matter are `enableSensors(false)` and the location provider factory. Read
 * section 7.2 before changing either: with sensors on, "the SDK ignores location updates which
 * don't match data from sensors" -- its own words -- and our feed would be silently dropped.
 */
object IdrMapboxNavigation {
    fun setup(context: Context) {
        if (MapboxNavigationApp.isSetup()) return
        val options = NavigationOptions.Builder(context.applicationContext)
            // R2. Never enable. See the class comment.
            .enableSensors(false)
            // R1. Our provider, declared REAL: it emits where the InEKF says the vehicle is.
            // Replay (section 7.9) uses the SDK's own MapboxReplayer with IS_MOCK, not this.
            .locationOptions(
                LocationOptions.Builder()
                    .locationProviderFactory(
                        DeviceLocationProviderFactory { _ ->
                            ExpectedFactory.createValue<LocationError, DeviceLocationProvider>(
                                InekfLocationProvider
                            )
                        },
                        LocationOptions.LocationProviderType.REAL
                    )
                    .build()
            )
            // R1. Prediction horizon matched to the feed cadence rather than the SDK default,
            // which is sized for a 1 Hz GNSS feed. Verify the default's value against 3.30.1.
            .navigatorPredictionMillis(InekfLocationProvider.CADENCE_MS)
            .build()
        MapboxNavigationApp.setup(options)
    }
}

package com.sih.idr.demo.ui.components

import androidx.activity.ComponentActivity
import com.mapbox.navigation.core.lifecycle.MapboxNavigationApp
import com.sih.idr.demo.backend.mapbox.IdrMapboxNavigation

/** The `mapbox` flavour: configure the Navigation SDK once, then attach this activity to it. */
object MapStack : MapStackHooks {
    override fun onActivityCreated(activity: ComponentActivity) {
        IdrMapboxNavigation.setup(activity)
        MapboxNavigationApp.attach(activity)
    }

    override val engineCaption: String = "Mapbox Navigation SDK v3, sensors off, fed by the on-device estimator at 10 Hz"
}

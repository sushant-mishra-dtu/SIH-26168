package com.sih.idr.demo.ui.components

import androidx.activity.ComponentActivity

/** The `osm` flavour has no SDK to initialise; OSMDroid is configured inside [MapView]. */
object MapStack : MapStackHooks {
    override fun onActivityCreated(activity: ComponentActivity) = Unit
    override val engineCaption: String = "OpenStreetMap tiles via OSMDroid"
}

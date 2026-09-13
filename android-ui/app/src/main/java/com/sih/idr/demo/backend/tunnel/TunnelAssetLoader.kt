package com.sih.idr.demo.backend.tunnel

import android.content.res.AssetManager
import android.util.Log
import org.json.JSONObject

/**
 * Loads tunnel definitions from a bundled JSON asset (D-126).
 *
 * Asset Schema:
 * ```json
 * {
 *   "schema": "idr.tunnels.v1",
 *   "note": "<optional notes>",
 *   "tunnels": [
 *     {
 *       "id": "demo-tunnel-1",
 *       "name": "<placeholder name>",
 *       "centreline": [ {"lat": 0.0, "lon": 0.0}, ... ],   // ordered, entry portal first, >= 2 points
 *       "postedLimitKmh": null                             // integer or null; null = not declared
 *     }
 *   ]
 * }
 * ```
 */
object TunnelAssetLoader {
    private const val TAG = "IDRTunnelAssetLoader"
    const val EXPECTED_SCHEMA = "idr.tunnels.v1"

    /**
     * Loads and parses tunnel definitions from the specified asset file.
     *
     * If the asset is missing, unreadable, or carries a schema other than [EXPECTED_SCHEMA],
     * an empty [TunnelGeometry] is returned and a warning is logged once. Never crashes the caller.
     */
    fun load(assets: AssetManager, fileName: String = "tunnels.json"): TunnelGeometry {
        val jsonString = try {
            assets.open(fileName).bufferedReader().use { it.readText() }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to read asset '$fileName': ${e.message}")
            return TunnelGeometry(emptyList())
        }

        return try {
            val root = JSONObject(jsonString)
            val schema = root.optString("schema")
            if (schema != EXPECTED_SCHEMA) {
                Log.w(TAG, "Rejecting '$fileName': schema was '$schema', expected '$EXPECTED_SCHEMA'")
                return TunnelGeometry(emptyList())
            }

            val tunnelsArray = root.optJSONArray("tunnels")
            if (tunnelsArray == null) {
                Log.w(TAG, "No 'tunnels' array found in '$fileName'")
                return TunnelGeometry(emptyList())
            }

            val tunnels = mutableListOf<TunnelDef>()
            for (i in 0 until tunnelsArray.length()) {
                val obj = tunnelsArray.optJSONObject(i) ?: continue
                val id = obj.optString("id")
                val name = obj.optString("name")
                val centrelineArray = obj.optJSONArray("centreline") ?: continue

                val centreline = mutableListOf<LatLon>()
                for (j in 0 until centrelineArray.length()) {
                    val pt = centrelineArray.optJSONObject(j) ?: continue
                    val lat = pt.optDouble("lat", Double.NaN)
                    val lon = pt.optDouble("lon", Double.NaN)
                    if (!lat.isNaN() && !lon.isNaN()) {
                        centreline.add(LatLon(lat, lon))
                    }
                }
                if (centreline.size < 2) {
                    Log.w(TAG, "Tunnel '$id' has fewer than 2 valid centreline points, skipping")
                    continue
                }

                val postedLimit = if (obj.has("postedLimitKmh") && !obj.isNull("postedLimitKmh")) {
                    obj.optInt("postedLimitKmh")
                } else {
                    null
                }

                val lengthM = computeCentrelineLengthM(centreline)
                tunnels.add(
                    TunnelDef(
                        id = id,
                        name = name,
                        centreline = centreline,
                        lengthM = lengthM,
                        postedLimitKmh = postedLimit
                    )
                )
            }
            Log.i(TAG, "Loaded ${tunnels.size} tunnel definitions from '$fileName'")
            TunnelGeometry(tunnels)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to parse '$fileName': ${e.message}")
            TunnelGeometry(emptyList())
        }
    }
}

package org.idr26168.logger.replay

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import org.idr26168.logger.R
import java.util.Locale

/**
 * Trajectory Replay Activity rendering `idr-trajectory/1` records produced by `eval/run.py`.
 *
 * **CRITICAL RULES (D-079, D-080, D-081):**
 * 1. NO physics and NO simulation. Reads `driftPct` and `yawErrorDeg` directly from the record.
 * 2. NO fallback that invents data when a file is missing. An empty state is shown when unloaded.
 * 3. Schema validation: refuses any record with an unrecognised schema string.
 * 4. Caption discipline (D-081): explicit statement that 200 Hz FOG configuration is not demonstrated.
 */
class ReplayActivity : AppCompatActivity() {

    private lateinit var stampText: TextView
    private lateinit var emptyStateView: View
    private lateinit var replayContentView: View
    private lateinit var loadButton: Button

    private lateinit var mapView: TrajectoryMapView
    private lateinit var seriesView: SeriesView
    private lateinit var sensorView: SensorTraceView

    private lateinit var scrubber: SeekBar
    private lateinit var readOutT: TextView
    private lateinit var readOutMetrics: TextView
    private lateinit var sensorCaption: TextView

    private var currentRecord: TrajectoryRecord? = null

    private val openDocumentLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val uri: Uri? = result.data?.data
            if (uri != null) {
                loadTrajectoryFromUri(uri)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_replay)

        stampText = findViewById(R.id.stamp)
        emptyStateView = findViewById(R.id.empty_state)
        replayContentView = findViewById(R.id.replay_content)
        loadButton = findViewById(R.id.load_json)

        mapView = findViewById(R.id.map_view)
        seriesView = findViewById(R.id.series_view)
        sensorView = findViewById(R.id.sensor_view)

        scrubber = findViewById(R.id.scrubber)
        readOutT = findViewById(R.id.r_t)
        readOutMetrics = findViewById(R.id.r_metrics)
        sensorCaption = findViewById(R.id.sensor_caption)

        loadButton.setOnClickListener {
            val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "*/*"
            }
            openDocumentLauncher.launch(intent)
        }

        scrubber.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                updateEpoch(progress)
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        // Check if an intent passed a trajectory URI directly
        intent?.data?.let { uri -> loadTrajectoryFromUri(uri) }
    }

    private fun loadTrajectoryFromUri(uri: Uri) {
        try {
            val jsonText = contentResolver.openInputStream(uri)?.use { stream ->
                stream.bufferedReader(Charsets.UTF_8).readText()
            } ?: throw IllegalArgumentException("Unable to read content from file.")

            val record = TrajectoryRecord.fromJson(jsonText)
            displayRecord(record)
        } catch (e: Exception) {
            AlertDialog.Builder(this)
                .setTitle("Invalid Trajectory Record")
                .setMessage(e.message ?: "Failed to parse JSON file.")
                .setPositiveButton("OK", null)
                .show()
        }
    }

    fun displayRecord(record: TrajectoryRecord) {
        currentRecord = record
        emptyStateView.visibility = View.GONE
        replayContentView.visibility = View.VISIBLE

        val dirtyNote = if (!record.reproducible) "  — NOT REPRODUCIBLE" else ""
        stampText.text = "${record.stamp}$dirtyNote"

        val maxEpoch = (record.epochS.size - 1).coerceAtLeast(0)
        scrubber.max = maxEpoch
        scrubber.progress = maxEpoch

        // Caption discipline (D-081)
        sensorCaption.text = String.format(
            Locale.US,
            "%s smartphone stream at %d Hz — %d samples over %d s. " +
                "Accelerometer m/s² (solid), gyroscope rad/s (dashed). This is the phone rate; " +
                "the 200 Hz FOG configuration is not demonstrated on this dataset.",
            record.stream,
            record.imuRateHz,
            record.accelMps2.size,
            record.lengthS,
        )

        updateEpoch(maxEpoch)
    }

    private fun updateEpoch(k: Int) {
        val r = currentRecord ?: return
        val validK = k.coerceIn(0, (r.epochS.size - 1).coerceAtLeast(0))

        val epochSec = if (validK < r.epochS.size) r.epochS[validK] else validK
        val driftPct = if (validK < r.driftPct.size) r.driftPct[validK] else 0.0
        val yawErrDeg = if (validK < r.yawErrorDeg.size) r.yawErrorDeg[validK] else 0.0
        val sig = if (validK < r.positionSigmaM.size) r.positionSigmaM[validK] else doubleArrayOf(0.0, 0.0)

        readOutT.text = String.format(Locale.US, "t into outage: %d s", epochSec)

        readOutMetrics.text = String.format(
            Locale.US,
            "drift, %% of distance: %.2f %%\n" +
                "yaw error: %.2f°\n" +
                "position σ north: %.2f m, east: %.2f m\n" +
                "truth distance: %.1f m   outage length: %d s   sequence: %s",
            driftPct,
            yawErrDeg,
            sig[0],
            sig[1],
            r.distanceM,
            r.lengthS,
            r.sequence,
        )

        mapView.setRecord(r, validK)
        seriesView.setRecord(r, validK)
        sensorView.setRecord(r, validK)
    }
}

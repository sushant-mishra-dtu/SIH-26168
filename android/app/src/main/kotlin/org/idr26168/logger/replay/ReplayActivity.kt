package org.idr26168.logger.replay

import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import org.idr26168.logger.R
import java.io.InputStream
import java.util.Locale

/**
 * Activity presenting the offline trajectory replay view.
 *
 * Implements the demo UI required by `android/HANDOVER.md` §3a and `android/README.md`.
 *
 * CRITICAL ARCHITECTURAL CONSTRAINTS:
 * - D-039 / D-080: This screen contains NO simulation and NO network.
 * - D-079: Drift-% and yaw error are read from the record, NEVER computed here.
 * - D-081: The sensor caption identifies the S- smartphone stream at 10 Hz and disclaims
 *   that the 200 Hz FOG configuration is not demonstrated on this dataset.
 */
class ReplayActivity : AppCompatActivity() {

    private val records = LinkedHashMap<String, TrajectoryRecord>()
    private var current: TrajectoryRecord? = null

    // UI elements
    private lateinit var stampView: TextView
    private lateinit var emptyState: View
    private lateinit var replayContent: View
    private lateinit var sequenceSpinner: Spinner
    private lateinit var btnLoadJson: Button
    private lateinit var btnEmptyLoad: Button

    private lateinit var trajectoryMap: TrajectoryMapView
    private lateinit var trajectorySeries: TrajectorySeriesView
    private lateinit var trajectoryImu: TrajectoryImuView
    private lateinit var epochScrubber: SeekBar

    private lateinit var readoutT: TextView
    private lateinit var readoutDrift: TextView
    private lateinit var readoutYaw: TextView
    private lateinit var readoutSn: TextView
    private lateinit var readoutSe: TextView
    private lateinit var readoutDist: TextView
    private lateinit var readoutLen: TextView
    private lateinit var readoutSeq: TextView
    private lateinit var imuCaption: TextView

    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.OpenMultipleDocuments()
    ) { uris: List<Uri> ->
        if (uris.isNotEmpty()) {
            for (uri in uris) {
                loadFromUri(uri)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_replay)

        stampView = findViewById(R.id.replay_stamp)
        emptyState = findViewById(R.id.empty_state)
        replayContent = findViewById(R.id.replay_content)
        sequenceSpinner = findViewById(R.id.sequence_spinner)
        btnLoadJson = findViewById(R.id.btn_load_json)
        btnEmptyLoad = findViewById(R.id.btn_empty_load)

        trajectoryMap = findViewById(R.id.trajectory_map)
        trajectorySeries = findViewById(R.id.trajectory_series)
        trajectoryImu = findViewById(R.id.trajectory_imu)
        epochScrubber = findViewById(R.id.epoch_scrubber)

        readoutT = findViewById(R.id.readout_t)
        readoutDrift = findViewById(R.id.readout_drift)
        readoutYaw = findViewById(R.id.readout_yaw)
        readoutSn = findViewById(R.id.readout_sn)
        readoutSe = findViewById(R.id.readout_se)
        readoutDist = findViewById(R.id.readout_dist)
        readoutLen = findViewById(R.id.readout_len)
        readoutSeq = findViewById(R.id.readout_seq)
        imuCaption = findViewById(R.id.imu_caption)

        btnLoadJson.setOnClickListener { openFilePicker() }
        btnEmptyLoad.setOnClickListener { openFilePicker() }

        epochScrubber.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                renderEpoch(progress)
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        sequenceSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val seq = parent?.getItemAtPosition(position) as? String ?: return
                selectRecord(seq)
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        // Handle intent if opened via file manager
        intent?.data?.let { uri ->
            loadFromUri(uri)
        }
    }

    private fun openFilePicker() {
        filePickerLauncher.launch(arrayOf("application/json", "*/*"))
    }

    private fun loadFromUri(uri: Uri) {
        val label = uri.lastPathSegment ?: "file"
        try {
            val content = contentResolver.openInputStream(uri)?.use { stream: InputStream ->
                stream.bufferedReader().readText()
            } ?: throw IllegalStateException("Could not read file $label")

            val record = TrajectoryParser.parse(content, label)
            accept(record)
        } catch (e: Exception) {
            AlertDialog.Builder(this)
                .setTitle("Invalid Trajectory Record")
                .setMessage(e.message ?: "Failed to parse trajectory JSON")
                .setPositiveButton("OK", null)
                .show()
        }
    }

    fun accept(record: TrajectoryRecord) {
        records[record.sequence] = record
        updateSpinner()
        selectRecord(record.sequence)
    }

    private fun updateSpinner() {
        if (records.size > 1) {
            val names = records.keys.toList().sorted()
            val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, names)
            sequenceSpinner.adapter = adapter
            sequenceSpinner.visibility = View.VISIBLE
        } else {
            sequenceSpinner.visibility = View.GONE
        }
    }

    private fun selectRecord(sequence: String) {
        val r = records[sequence] ?: return
        current = r

        emptyState.visibility = View.GONE
        replayContent.visibility = View.VISIBLE

        val dirtyNote = if (!r.reproducible) " — NOT REPRODUCIBLE" else ""
        stampView.text = "${r.stamp}$dirtyNote"
        if (!r.reproducible) {
            stampView.setTextColor(android.graphics.Color.parseColor("#F85149"))
        } else {
            stampView.setTextColor(android.graphics.Color.parseColor("#8B949E"))
        }

        readoutSeq.text = r.sequence
        readoutLen.text = "${r.lengthS}"
        readoutDist.text = String.format(Locale.US, "%.1f", r.distanceM)

        imuCaption.text = String.format(
            Locale.US,
            "%s smartphone stream at %d Hz — %d samples over %d s. " +
            "Accelerometer m/s² (solid), gyroscope rad/s (dashed). This is the phone rate; " +
            "the 200 Hz FOG configuration is not demonstrated on this dataset.",
            r.stream, r.imuRateHz, r.accelMps2.size, r.lengthS,
        )

        val n = r.epochS.size
        epochScrubber.max = (n - 1).coerceAtLeast(0)
        // Match replay.html: open at the final scrubbed epoch
        epochScrubber.progress = (n - 1).coerceAtLeast(0)
        renderEpoch((n - 1).coerceAtLeast(0))
    }

    private fun renderEpoch(k: Int) {
        val r = current ?: return
        val clampedK = k.coerceIn(0, r.epochS.size - 1)

        val tSec = if (clampedK < r.epochS.size) r.epochS[clampedK] else clampedK
        readoutT.text = "$tSec s"

        val drift = if (clampedK < r.driftPct.size) r.driftPct[clampedK] else 0.0
        readoutDrift.text = String.format(Locale.US, "%.2f %%", drift)

        val yawErr = if (clampedK < r.yawErrorDeg.size) r.yawErrorDeg[clampedK] else 0.0
        readoutYaw.text = String.format(Locale.US, "%.2f°", yawErr)

        if (clampedK < r.positionSigmaM.size) {
            val sig = r.positionSigmaM[clampedK]
            readoutSn.text = String.format(Locale.US, "%.2f", sig.sigmaNorth)
            readoutSe.text = String.format(Locale.US, "%.2f", sig.sigmaEast)
        } else {
            readoutSn.text = "—"
            readoutSe.text = "—"
        }

        trajectoryMap.bind(r, clampedK)
        trajectorySeries.bind(r, clampedK)
        trajectoryImu.bind(r, clampedK)
    }
}

package org.idr26168.logger

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import org.idr26168.logger.replay.ReplayActivity
import java.io.File
import java.util.Locale

/**
 * One screen: start, stop, achieved rate and jitter while recording, export session zip,
 * and trajectory replay view.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var status: TextView
    private lateinit var session: TextView
    private lateinit var rates: TextView
    private lateinit var gnss: TextView
    private lateinit var warnings: TextView
    private lateinit var startButton: Button
    private lateinit var stopButton: Button
    private lateinit var exportButton: Button
    private lateinit var replayButton: Button

    private var pendingExportSessionDir: File? = null

    private val ui = Handler(Looper.getMainLooper())

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        if (granted[Manifest.permission.ACCESS_FINE_LOCATION] == true) {
            startService()
        } else {
            status.text = "Location permission denied. A recording without GNSS has no reference " +
                "track and will not be started."
        }
    }

    private val createDocumentLauncher = registerForActivityResult(
        ActivityResultContracts.CreateDocument("application/zip")
    ) { uri: Uri? ->
        val sessionDir = pendingExportSessionDir
        if (uri != null && sessionDir != null) {
            try {
                contentResolver.openOutputStream(uri)?.use { out ->
                    val zipped = SessionExporter.zipSession(sessionDir, out)
                    Toast.makeText(
                        this,
                        "Exported ${zipped.size} files for session ${sessionDir.name}",
                        Toast.LENGTH_LONG,
                    ).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this, "Export failed: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private val refresh = object : Runnable {
        override fun run() {
            render(LoggerState.current)
            ui.postDelayed(this, REFRESH_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        status = findViewById(R.id.status)
        session = findViewById(R.id.session)
        rates = findViewById(R.id.rates)
        gnss = findViewById(R.id.gnss)
        warnings = findViewById(R.id.warnings)
        startButton = findViewById(R.id.start)
        stopButton = findViewById(R.id.stop)
        exportButton = findViewById(R.id.export_session)
        replayButton = findViewById(R.id.open_replay)

        startButton.setOnClickListener { requestPermissionsThenStart() }
        stopButton.setOnClickListener {
            startService(Intent(this, LoggerService::class.java).setAction(LoggerService.ACTION_STOP))
        }

        exportButton.setOnClickListener { exportLatestSession() }
        replayButton.setOnClickListener {
            startActivity(Intent(this, ReplayActivity::class.java))
        }
    }

    override fun onResume() {
        super.onResume()
        ui.post(refresh)
    }

    override fun onPause() {
        super.onPause()
        ui.removeCallbacks(refresh)
    }

    private fun exportLatestSession() {
        val baseDir = File(getExternalFilesDir(null) ?: filesDir, "sessions")
        val sessions = baseDir.listFiles()?.filter { it.isDirectory && it.listFiles()?.isNotEmpty() == true }
            ?.sortedByDescending { it.name } ?: emptyList()

        if (sessions.isEmpty()) {
            Toast.makeText(this, "No recorded sessions found to export.", Toast.LENGTH_SHORT).show()
            return
        }

        val targetSession = sessions.first()
        pendingExportSessionDir = targetSession
        createDocumentLauncher.launch("${targetSession.name}.zip")
    }

    private fun requestPermissionsThenStart() {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) {
            needed += Manifest.permission.ACCESS_FINE_LOCATION
            needed += Manifest.permission.ACCESS_COARSE_LOCATION
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            needed += Manifest.permission.POST_NOTIFICATIONS
        }

        if (needed.isEmpty()) startService() else permissionLauncher.launch(needed.toTypedArray())
    }

    private fun startService() {
        val intent = Intent(this, LoggerService::class.java)
            .setAction(LoggerService.ACTION_START)
            .putExtra(LoggerService.EXTRA_IMU_HZ, LoggerService.DEFAULT_IMU_HZ)
        ContextCompat.startForegroundService(this, intent)
    }

    private fun render(s: LoggerState.Snapshot) {
        startButton.isEnabled = !s.running
        stopButton.isEnabled = s.running

        if (!s.running) {
            status.text = "Idle"
            session.text = "No session"
            rates.text = "Not recording."
            gnss.text = "No fix."
            warnings.visibility = android.view.View.GONE
            return
        }

        status.text = String.format(
            Locale.US,
            "Recording  %s  %,d rows  %.1f MB",
            hms(s.elapsedS), s.csvRows, s.bytesOnDisk / 1e6,
        )

        session.text = buildString {
            append(s.sessionId).append('\n')
            append(s.sessionDir).append('\n')
            append("sensor timebase: ").append(s.timebase)
            if (s.csvDropped > 0 || s.rawDropped > 0) {
                append("\ndropped: csv ").append(s.csvDropped).append(", raw ").append(s.rawDropped)
            }
        }

        rates.text = buildString {
            append(String.format(
                Locale.US, "%-28s %7s %7s %7s %7s %7s\n",
                "stream", "req Hz", "got Hz", "med ms", "p95 ms", "sd ms"
            ))
            for (st in s.streams) {
                append(
                    String.format(
                        Locale.US,
                        "%-28s %7.1f %7.2f %7.2f %7.2f %7.2f\n",
                        st.label, st.requestedHz, st.achievedHz,
                        st.dtMedianMs, st.dtP95Ms, st.dtStdevMs,
                    )
                )
                if (st.nonMonotonic > 0 || st.batchArrivals > 0) {
                    append(
                        String.format(
                            Locale.US,
                            "%-28s non-monotonic %d, batched %d\n",
                            "", st.nonMonotonic, st.batchArrivals,
                        )
                    )
                }
            }
        }

        val g = s.gnss
        gnss.text = if (g == null || g.fixes == 0L) {
            "No fix yet."
        } else {
            String.format(
                Locale.US,
                "fixes %d   age %.1f s   accuracy %.1f m\nsats %d in view, %d used   mean C/N0 %.1f dB-Hz",
                g.fixes, g.ageS, g.accuracyM, g.satsInView, g.usedInFix, g.meanCn0DbHz,
            )
        }

        if (s.warnings.isEmpty()) {
            warnings.visibility = android.view.View.GONE
        } else {
            warnings.visibility = android.view.View.VISIBLE
            warnings.text = s.warnings.joinToString("\n\n")
        }
    }

    private fun hms(seconds: Double): String {
        val total = seconds.toLong()
        return String.format(Locale.US, "%02d:%02d:%02d", total / 3600, (total % 3600) / 60, total % 60)
    }

    companion object {
        private const val REFRESH_MS = 500L
    }
}

package org.idr26168.logger.replay

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.View
import kotlin.math.abs
import kotlin.math.max

/**
 * Custom Canvas View plotting drift-% (blue) and |yaw error| in degrees (amber) across epochs.
 *
 * Implements the series scrubber plot in `eval/replay/replay.html`.
 *
 * CRITICAL RULE (D-079): Drift-% and yaw error values are read verbatim from the record;
 * they are NEVER computed or scaled here.
 */
class TrajectorySeriesView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0,
) : View(context, attrs, defStyleAttr) {

    private var record: TrajectoryRecord? = null
    private var scrubEpoch: Int = 0

    private val density = context.resources.displayMetrics.density
    private val margin = 24f * density

    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#30363D")
        strokeWidth = 1f * density
    }

    private val driftPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#2F81F7")
        strokeWidth = 1.8f * density
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val yawPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#D29922")
        strokeWidth = 1.8f * density
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val cursorPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#E6EDF3")
        strokeWidth = 1.2f * density
    }

    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#8B949E")
        textSize = 10f * density
    }

    private val path = Path()

    fun bind(trajectoryRecord: TrajectoryRecord?, epoch: Int) {
        this.record = trajectoryRecord
        this.scrubEpoch = epoch
        invalidate()
    }

    fun setScrubEpoch(epoch: Int) {
        this.scrubEpoch = epoch
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val r = record ?: return
        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0f || h <= 0f) return

        val n = r.epochS.size
        if (n <= 0) return

        val drift = r.driftPct
        val yawAbs = r.yawErrorDeg.map { abs(it) }

        var maxD = 1.0
        for (v in drift) { if (v > maxD) maxD = v }
        var maxY = 1.0
        for (v in yawAbs) { if (v > maxY) maxY = v }

        val availW = max(w - 2f * margin, 10f)
        val availH = max(h - 2f * margin, 10f)

        fun xPos(i: Int): Float =
            margin + (i.toFloat() / max((n - 1).toFloat(), 1f)) * availW

        // Baseline
        val baseY = h - margin
        canvas.drawLine(margin, baseY, w - margin, baseY, linePaint)

        // Plot drift curve
        path.reset()
        for (i in drift.indices) {
            val v = drift[i]
            val x = xPos(i)
            val y = baseY - (v.toFloat() / maxD.toFloat()) * availH
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        canvas.drawPath(path, driftPaint)

        // Plot yaw error curve
        path.reset()
        for (i in yawAbs.indices) {
            val v = yawAbs[i]
            val x = xPos(i)
            val y = baseY - (v.toFloat() / maxY.toFloat()) * availH
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        canvas.drawPath(path, yawPaint)

        // Vertical scrub cursor
        val k = scrubEpoch.coerceIn(0, n - 1)
        val cursorX = xPos(k)
        canvas.drawLine(cursorX, 8f * density, cursorX, baseY, cursorPaint)

        // Text labels
        canvas.drawText(String.format("drift max %.2f%%", maxD), margin, 14f * density, textPaint)
        canvas.drawText(String.format("|yaw| max %.2f°", maxY), margin + 140f * density, 14f * density, textPaint)
        canvas.drawText("0 s", margin, h - 4f * density, textPaint)
        canvas.drawText("${r.lengthS} s", w - margin - 24f * density, h - 4f * density, textPaint)
    }
}

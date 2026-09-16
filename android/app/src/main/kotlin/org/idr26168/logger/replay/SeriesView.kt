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
 * Canvas View rendering time-series plots of drift-% (blue) and |yaw error| in degrees (amber)
 * across outage epochs, with a vertical scrubber cursor at epoch k.
 */
class SeriesView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private var record: TrajectoryRecord? = null
    private var scrubbedEpoch: Int = 0

    private val driftPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#2F81F7")
        strokeWidth = 4f
        style = Paint.Style.STROKE
    }

    private val yawPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#D29922")
        strokeWidth = 4f
        style = Paint.Style.STROKE
    }

    private val cursorPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#E6EDF3")
        strokeWidth = 3f
        style = Paint.Style.STROKE
    }

    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#30363D")
        strokeWidth = 2f
        style = Paint.Style.STROKE
    }

    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#8B949E")
        textSize = 26f
    }

    private val path = Path()

    fun setRecord(record: TrajectoryRecord?, epoch: Int = 0) {
        this.record = record
        this.scrubbedEpoch = epoch
        invalidate()
    }

    fun setScrubbedEpoch(epoch: Int) {
        this.scrubbedEpoch = epoch
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val r = record ?: return
        val drift = r.driftPct
        val yaw = r.yawErrorDeg.map { abs(it) }
        val n = drift.size
        if (n == 0) return

        val w = width.toFloat()
        val h = height.toFloat()
        val margin = 40f
        val plotW = w - 2 * margin
        val plotH = h - 2 * margin

        // Baseline horizontal line
        canvas.drawLine(margin, h - margin, w - margin, h - margin, gridPaint)

        val maxD = max(drift.maxOrNull() ?: 1.0, 1.0)
        val maxY = max(yaw.maxOrNull() ?: 1.0, 1.0)

        fun mapX(index: Int): Float = margin + (index.toFloat() / max(n - 1, 1)) * plotW

        // Plot drift-%
        path.reset()
        drift.forEachIndexed { i, v ->
            val x = mapX(i)
            val y = h - margin - (v / maxD).toFloat() * plotH
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        canvas.drawPath(path, driftPaint)

        // Plot |yaw error|
        path.reset()
        yaw.forEachIndexed { i, v ->
            val x = mapX(i)
            val y = h - margin - (v / maxY).toFloat() * plotH
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        canvas.drawPath(path, yawPaint)

        // Draw cursor
        val k = scrubbedEpoch.coerceIn(0, n - 1)
        val cx = mapX(k)
        canvas.drawLine(cx, margin, cx, h - margin, cursorPaint)

        // Labels
        canvas.drawText(String.format("drift max %.2f%%", maxD), margin, margin, textPaint)
        canvas.drawText(String.format("|yaw| max %.2f°", maxY), margin + 250f, margin, textPaint)
        canvas.drawText("0 s", margin, h - 10f, textPaint)
        canvas.drawText("${r.lengthS} s", w - margin - 60f, h - 10f, textPaint)
    }
}

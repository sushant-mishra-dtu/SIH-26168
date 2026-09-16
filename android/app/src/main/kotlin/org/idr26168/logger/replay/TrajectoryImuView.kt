package org.idr26168.logger.replay

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.View
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * Custom Canvas View plotting raw 3-axis accelerometer (solid) and gyroscope (dashed) traces.
 *
 * Implements the sensor traces panel in `eval/replay/replay.html`.
 */
class TrajectoryImuView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0,
) : View(context, attrs, defStyleAttr) {

    private var record: TrajectoryRecord? = null
    private var scrubEpoch: Int = 0

    private val density = context.resources.displayMetrics.density
    private val margin = 24f * density

    private val midLinePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#30363D")
        strokeWidth = 1f * density
    }

    private val axisColors = intArrayOf(
        Color.parseColor("#F85149"), // X: Red
        Color.parseColor("#3FB950"), // Y: Green
        Color.parseColor("#2F81F7"), // Z: Blue
    )

    private val solidPaints = axisColors.map { col ->
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = col
            strokeWidth = 1f * density
            style = Paint.Style.STROKE
        }
    }

    private val dashedPaints = axisColors.map { col ->
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = col
            strokeWidth = 1f * density
            style = Paint.Style.STROKE
            pathEffect = DashPathEffect(floatArrayOf(3f * density, 3f * density), 0f)
        }
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

        val accel = r.accelMps2
        val gyro = r.gyroRps
        val n = accel.size
        if (n <= 0) return

        var maxA = 1.0
        for (v in accel) {
            maxA = max(maxA, abs(v.x))
            maxA = max(maxA, abs(v.y))
            maxA = max(maxA, abs(v.z))
        }

        var maxG = 1e-3
        for (v in gyro) {
            maxG = max(maxG, abs(v.x))
            maxG = max(maxG, abs(v.y))
            maxG = max(maxG, abs(v.z))
        }

        val availW = max(w - 2f * margin, 10f)
        val mid = h / 2f
        val availHalfH = max(mid - margin, 10f)

        fun xPos(i: Int): Float =
            margin + (i.toFloat() / max((n - 1).toFloat(), 1f)) * availW

        // Center baseline
        canvas.drawLine(margin, mid, w - margin, mid, midLinePaint)

        // Draw 3 axes
        for (ax in 0..2) {
            // Accel (solid)
            path.reset()
            for (i in 0 until n) {
                val pt = accel[i]
                val v = when (ax) {
                    0 -> pt.x
                    1 -> pt.y
                    else -> pt.z
                }
                val y = mid - (v.toFloat() / maxA.toFloat()) * availHalfH
                val x = xPos(i)
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            canvas.drawPath(path, solidPaints[ax])

            // Gyro (dashed)
            if (gyro.size == n) {
                path.reset()
                for (i in 0 until n) {
                    val pt = gyro[i]
                    val v = when (ax) {
                        0 -> pt.x
                        1 -> pt.y
                        else -> pt.z
                    }
                    val y = mid - (v.toFloat() / maxG.toFloat()) * availHalfH
                    val x = xPos(i)
                    if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
                }
                canvas.drawPath(path, dashedPaints[ax])
            }
        }

        // Scrub cursor
        val epochCount = max(r.epochS.size - 1, 1)
        val at = min(n - 1, ((scrubEpoch.toFloat() / epochCount.toFloat()) * (n - 1)).roundToInt())
        val cursorX = xPos(at)
        canvas.drawLine(cursorX, 6f * density, cursorX, h - 6f * density, cursorPaint)

        // Range caption
        canvas.drawText(
            String.format("±%.2f m/s² · ±%.3f rad/s", maxA, maxG),
            margin,
            14f * density,
            textPaint,
        )
    }
}

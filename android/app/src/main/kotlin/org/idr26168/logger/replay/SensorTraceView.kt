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
import kotlin.math.roundToInt

/**
 * Canvas View rendering 10 Hz accelerometer (m/s², solid lines) and gyroscope (rad/s, dashed)
 * sensor traces with a vertical scrubber cursor.
 */
class SensorTraceView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private var record: TrajectoryRecord? = null
    private var scrubbedEpoch: Int = 0

    // Axes colors: X = red (#F85149), Y = green (#3FB950), Z = blue (#2F81F7)
    private val axesColors = intArrayOf(
        Color.parseColor("#F85149"),
        Color.parseColor("#3FB950"),
        Color.parseColor("#2F81F7"),
    )

    private val solidPaints = Array(3) { i ->
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = axesColors[i]
            strokeWidth = 3f
            style = Paint.Style.STROKE
        }
    }

    private val dashPaints = Array(3) { i ->
        Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = axesColors[i]
            strokeWidth = 3f
            style = Paint.Style.STROKE
            pathEffect = DashPathEffect(floatArrayOf(6f, 6f), 0f)
        }
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
        val accel = r.accelMps2
        val gyro = r.gyroRps
        val n = accel.size
        if (n == 0) return

        val w = width.toFloat()
        val h = height.toFloat()
        val margin = 40f
        val plotW = w - 2 * margin
        val plotH = h - 2 * margin
        val midY = h / 2f

        // Center zero line
        canvas.drawLine(margin, midY, w - margin, midY, gridPaint)

        var maxA = 1.0
        for (a in accel) {
            for (v in a) maxA = max(maxA, abs(v))
        }

        var maxG = 1e-3
        for (g in gyro) {
            for (v in g) maxG = max(maxG, abs(v))
        }

        fun mapX(index: Int): Float = margin + (index.toFloat() / max(n - 1, 1)) * plotW

        // Plot 3 accel axes (solid) and 3 gyro axes (dashed)
        for (ax in 0 until 3) {
            // Accel
            path.reset()
            for (i in 0 until n) {
                val x = mapX(i)
                val v = accel[i][ax]
                val y = midY - (v / maxA).toFloat() * (plotH / 2f)
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            canvas.drawPath(path, solidPaints[ax])

            // Gyro
            if (gyro.size == n) {
                path.reset()
                for (i in 0 until n) {
                    val x = mapX(i)
                    val v = gyro[i][ax]
                    val y = midY - (v / maxG).toFloat() * (plotH / 2f)
                    if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
                }
                canvas.drawPath(path, dashPaints[ax])
            }
        }

        // Draw cursor index corresponding to epoch k
        val totalEpochs = max(r.epochS.size - 1, 1)
        val k = scrubbedEpoch.coerceIn(0, totalEpochs)
        val sampleIndex = ((k.toFloat() / totalEpochs) * (n - 1)).roundToInt().coerceIn(0, n - 1)
        val cx = mapX(sampleIndex)
        canvas.drawLine(cx, margin, cx, h - margin, cursorPaint)

        // Caption label
        canvas.drawText(
            String.format("±%.2f m/s²  ·  ±%.3f rad/s", maxA, maxG),
            margin,
            margin,
            textPaint,
        )
    }
}

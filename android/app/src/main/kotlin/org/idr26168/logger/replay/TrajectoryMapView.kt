package org.idr26168.logger.replay

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import kotlin.math.max
import kotlin.math.min

/**
 * 2D Canvas View rendering local NED trajectories and the 1σ filter covariance ellipse.
 *
 * Ground truth (white), filter (blue), strapdown (red), GNSS (amber).
 * North is +Y upward, East is +X rightward.
 */
class TrajectoryMapView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private var record: TrajectoryRecord? = null
    private var scrubbedEpoch: Int = 0

    private val truthPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#E6EDF3")
        strokeWidth = 5f
        style = Paint.Style.STROKE
    }

    private val filterPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#2F81F7")
        strokeWidth = 4f
        style = Paint.Style.STROKE
    }

    private val strapdownPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#F85149")
        strokeWidth = 4f
        style = Paint.Style.STROKE
    }

    private val gnssPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#D29922")
        strokeWidth = 4f
        style = Paint.Style.STROKE
    }

    private val ellipsePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#2F81F7")
        strokeWidth = 3f
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(8f, 8f), 0f)
    }

    private val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }

    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#8B949E")
        textSize = 30f
    }

    private val path = Path()
    private val ellipseRect = RectF()

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
        if (r.epochS.isEmpty()) return

        val k = scrubbedEpoch.coerceIn(0, r.epochS.size - 1)
        val series = listOfNotNull(r.truthNed, r.filterNed, r.strapdownNed, r.gnssNed)

        // Compute extent over all positions plus 1σ ellipse padding
        var minN = Double.POSITIVE_INFINITY
        var maxN = Double.NEGATIVE_INFINITY
        var minE = Double.POSITIVE_INFINITY
        var maxE = Double.NEGATIVE_INFINITY

        for (s in series) {
            for (p in s) {
                if (p.size >= 2) {
                    minN = min(minN, p[0])
                    maxN = max(maxN, p[0])
                    minE = min(minE, p[1])
                    maxE = max(maxE, p[1])
                }
            }
        }

        var maxSigma = 1.0
        for (sig in r.positionSigmaM) {
            if (sig.size >= 2) {
                maxSigma = max(maxSigma, max(sig[0], sig[1]))
            }
        }

        val pad = maxSigma * 2.0
        minN -= pad; maxN += pad
        minE -= pad; maxE += pad

        val spanN = max(maxN - minN, 1e-6)
        val spanE = max(maxE - minE, 1e-6)

        val margin = 50f
        val w = width.toFloat()
        val h = height.toFloat()
        val availW = w - 2 * margin
        val availH = h - 2 * margin

        val scale = min(availW / spanE, availH / spanN).toFloat()

        // East is X rightward, North is Y upward (canvas Y is inverted)
        fun mapX(e: Double): Float =
            margin + ((e - minE) * scale).toFloat() + (availW - spanE.toFloat() * scale) / 2f

        fun mapY(n: Double): Float =
            h - margin - ((n - minN) * scale).toFloat() - (availH - spanN.toFloat() * scale) / 2f

        // Draw trajectories up to scrubbed epoch k
        val tracks = listOf(
            r.truthNed to truthPaint,
            r.filterNed to filterPaint,
            r.strapdownNed to strapdownPaint,
            r.gnssNed to gnssPaint,
        )

        for ((track, paint) in tracks) {
            if (track == null || track.isEmpty()) continue
            path.reset()
            val limit = min(k, track.size - 1)
            for (i in 0..limit) {
                val p = track[i]
                val x = mapX(p[1])
                val y = mapY(p[0])
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            canvas.drawPath(path, paint)

            // Draw dot at current epoch k
            if (limit < track.size) {
                val curP = track[limit]
                dotPaint.color = paint.color
                val radius = if (paint == truthPaint) 10f else 8f
                canvas.drawCircle(mapX(curP[1]), mapY(curP[0]), radius, dotPaint)
            }
        }

        // Draw 1σ covariance ellipse around filter position at epoch k
        if (k < r.filterNed.size && k < r.positionSigmaM.size) {
            val centerP = r.filterNed[k]
            val sigma = r.positionSigmaM[k]
            val cx = mapX(centerP[1])
            val cy = mapY(centerP[0])
            val sigmaN = (sigma[0] * scale).toFloat().coerceAtLeast(2f)
            val sigmaE = (sigma[1] * scale).toFloat().coerceAtLeast(2f)

            ellipseRect.set(cx - sigmaE, cy - sigmaN, cx + sigmaE, cy + sigmaN)
            canvas.drawOval(ellipseRect, ellipsePaint)
        }

        // Render bounds text and North arrow
        val scaleText = String.format("%.0f m east × %.0f m north", spanE, spanN)
        canvas.drawText(scaleText, margin, margin + 10f, textPaint)
        canvas.drawText("N ↑", w - margin - 60f, h - margin, textPaint)
    }
}

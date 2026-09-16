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
 * 2D Canvas View rendering local NED trajectories and the 1σ position uncertainty ellipse.
 *
 * Implements the vector map view defined in `eval/replay/replay.html` and `android/HANDOVER.md` §3a.
 *
 * Tracks:
 * - Ground truth (V- VBOX, 10 Hz): #E6EDF3 (solid light)
 * - Ours — InEKF: #2F81F7 (blue)
 * - Naive strapdown baseline: #F85149 (red)
 * - GNSS available: #D29922 (amber)
 *
 * Uncertainty:
 * - Dashed ellipse around the InEKF position marker showing 1σ north/east covariance.
 */
class TrajectoryMapView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0,
) : View(context, attrs, defStyleAttr) {

    private var record: TrajectoryRecord? = null
    private var scrubEpoch: Int = 0

    private val density = context.resources.displayMetrics.density
    private val margin = 28f * density

    // Track paints
    private val truthPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#E6EDF3")
        strokeWidth = 2.5f * density
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val filterPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#2F81F7")
        strokeWidth = 1.8f * density
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val strapdownPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#F85149")
        strokeWidth = 1.8f * density
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val gnssPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#D29922")
        strokeWidth = 1.8f * density
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
    }

    private val ellipsePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#2F81F7")
        strokeWidth = 1.2f * density
        style = Paint.Style.STROKE
        pathEffect = DashPathEffect(floatArrayOf(4f * density, 4f * density), 0f)
    }

    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#8B949E")
        textSize = 11f * density
    }

    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#30363D")
        strokeWidth = 1f * density
        style = Paint.Style.STROKE
    }

    private val path = Path()
    private val ellipseRect = RectF()

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

        // Compute coordinate extent over all series + position sigma padding
        var loN = Double.POSITIVE_INFINITY
        var hiN = Double.NEGATIVE_INFINITY
        var loE = Double.POSITIVE_INFINITY
        var hiE = Double.NEGATIVE_INFINITY

        fun updateExtent(list: List<NedPoint>?) {
            if (list == null) return
            for (p in list) {
                if (p.north < loN) loN = p.north
                if (p.north > hiN) hiN = p.north
                if (p.east < loE) loE = p.east
                if (p.east > hiE) hiE = p.east
            }
        }

        updateExtent(r.truthNed)
        updateExtent(r.filterNed)
        updateExtent(r.strapdownNed)
        updateExtent(r.gnssNed)

        var maxSigma = 1.0
        for (s in r.positionSigmaM) {
            if (s.sigmaNorth > maxSigma) maxSigma = s.sigmaNorth
            if (s.sigmaEast > maxSigma) maxSigma = s.sigmaEast
        }
        val pad = max(maxSigma * 2.0, 1.0)
        loN -= pad
        hiN += pad
        loE -= pad
        hiE += pad

        val spanN = max(hiN - loN, 1e-6)
        val spanE = max(hiE - loE, 1e-6)

        val availW = max(w - 2f * margin, 10f)
        val availH = max(h - 2f * margin, 10f)
        val scale = min(availW / spanE.toFloat(), availH / spanN.toFloat())

        // East is x (to the right); North is y (upward, so inverted from canvas y)
        fun xPos(p: NedPoint): Float =
            margin + ((p.east - loE).toFloat() * scale) + (availW - spanE.toFloat() * scale) / 2f

        fun yPos(p: NedPoint): Float =
            h - margin - ((p.north - loN).toFloat() * scale) - (availH - spanN.toFloat() * scale) / 2f

        val k = min(scrubEpoch, r.epochS.size - 1)

        // Draw border/grid frame
        canvas.drawRect(margin / 2f, margin / 2f, w - margin / 2f, h - margin / 2f, gridPaint)

        // Helper to draw a single track up to epoch k
        fun drawTrack(list: List<NedPoint>?, paint: Paint, markerColor: Int, markerRadius: Float) {
            if (list == null || list.isEmpty()) return
            path.reset()
            val endIdx = min(k, list.size - 1)
            for (i in 0..endIdx) {
                val pt = list[i]
                val x = xPos(pt)
                val y = yPos(pt)
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            canvas.drawPath(path, paint)

            if (endIdx >= 0 && endIdx < list.size) {
                val cur = list[endIdx]
                markerPaint.color = markerColor
                canvas.drawCircle(xPos(cur), yPos(cur), markerRadius, markerPaint)
            }
        }

        // Draw all 4 series in order: GNSS, Strapdown, Filter, Truth
        drawTrack(r.gnssNed, gnssPaint, Color.parseColor("#D29922"), 3f * density)
        drawTrack(r.strapdownNed, strapdownPaint, Color.parseColor("#F85149"), 3f * density)
        drawTrack(r.filterNed, filterPaint, Color.parseColor("#2F81F7"), 3f * density)
        drawTrack(r.truthNed, truthPaint, Color.parseColor("#E6EDF3"), 4f * density)

        // Draw 1σ covariance ellipse around the InEKF position at epoch k
        if (k < r.filterNed.size && k < r.positionSigmaM.size) {
            val curFilter = r.filterNed[k]
            val sigma = r.positionSigmaM[k]
            val cx = xPos(curFilter)
            val cy = yPos(curFilter)
            val rx = max(sigma.sigmaEast.toFloat() * scale, 1.5f * density)
            val ry = max(sigma.sigmaNorth.toFloat() * scale, 1.5f * density)

            ellipseRect.set(cx - rx, cy - ry, cx + rx, cy + ry)
            canvas.drawOval(ellipseRect, ellipsePaint)
        }

        // Scale and North indicators
        val spanText = String.format("%.0f m east × %.0f m north", spanE, spanN)
        canvas.drawText(spanText, margin, 18f * density, textPaint)
        canvas.drawText("N ↑", w - margin - 22f * density, h - margin / 2f - 4f * density, textPaint)
    }
}

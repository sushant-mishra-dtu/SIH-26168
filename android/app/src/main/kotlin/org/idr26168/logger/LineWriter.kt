package org.idr26168.logger

import java.io.BufferedWriter
import java.io.File
import java.io.OutputStreamWriter
import java.nio.charset.Charset
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong

/**
 * A file, a bounded queue, and one thread that drains it.
 *
 * The rule this enforces: **a sensor callback never blocks on I/O.** It offers a value and returns.
 * If the queue is full the value is dropped and counted -- dropped-and-counted beats a blocked
 * callback, because blocking the sensor thread does not lose one sample, it perturbs the delivery
 * of every subsequent one and corrupts the very jitter figure this app exists to measure.
 *
 * Formatting happens on the writer thread, not the producer's, for the same reason: the producer
 * hands over the raw value and pays nothing but an enqueue.
 *
 * Encoding is ISO-8859-1 and not UTF-8. `eval/loaders/io_vnbd.py` reads with
 * `encoding="latin-1"`, so writing latin-1 makes the round-trip exact. Our headers are ASCII
 * anyway (see [Channels]), which means the two encodings agree byte for byte on every file we
 * write -- the explicit charset is here so that stays true if someone later adds a degree sign.
 */
class LineWriter<T>(
    private val file: File,
    private val header: String?,
    capacity: Int,
    private val format: (T, StringBuilder) -> Unit,
) {

    private val queue = ArrayBlockingQueue<T>(capacity)
    private val written = AtomicLong(0)
    private val dropped = AtomicLong(0)

    @Volatile private var running = false
    private var thread: Thread? = null

    fun start() {
        if (running) return
        running = true
        val t = Thread({ drain() }, "line-writer-" + file.name)
        t.priority = Thread.NORM_PRIORITY
        thread = t
        t.start()
    }

    /** Non-blocking. Returns false if the value was dropped. */
    fun offer(value: T): Boolean {
        if (!running) return false
        val ok = queue.offer(value)
        if (!ok) dropped.incrementAndGet()
        return ok
    }

    /**
     * Stop accepting, drain what is already queued, then close.
     *
     * Draining rather than discarding matters: the last seconds of a recording are the ones the
     * driver remembers, and a file that silently ends 3 s early is a file whose end nobody trusts.
     */
    fun stop() {
        running = false
        thread?.join(STOP_DRAIN_TIMEOUT_MS)
        thread = null
    }

    fun written(): Long = written.get()

    fun dropped(): Long = dropped.get()

    fun path(): String = file.absolutePath

    fun sizeBytes(): Long = if (file.exists()) file.length() else 0L

    private fun drain() {
        val charset: Charset = Charsets.ISO_8859_1
        BufferedWriter(OutputStreamWriter(file.outputStream(), charset), BUFFER_BYTES).use { out ->
            header?.let {
                out.write(it)
                out.write("\n")
            }
            val sb = StringBuilder(512)
            var sinceFlush = 0
            var lastFlushMs = System.currentTimeMillis()

            while (true) {
                val value = queue.poll(POLL_MS, TimeUnit.MILLISECONDS)
                if (value == null) {
                    if (!running && queue.isEmpty()) break
                    // A quiet period is still a reason to flush: a crash mid-drive should cost
                    // seconds of data, not the whole session.
                    if (sinceFlush > 0) {
                        out.flush()
                        sinceFlush = 0
                        lastFlushMs = System.currentTimeMillis()
                    }
                    continue
                }

                sb.setLength(0)
                format(value, sb)
                sb.append('\n')
                out.write(sb.toString())
                written.incrementAndGet()
                sinceFlush++

                val now = System.currentTimeMillis()
                if (sinceFlush >= FLUSH_ROWS || now - lastFlushMs >= FLUSH_INTERVAL_MS) {
                    out.flush()
                    sinceFlush = 0
                    lastFlushMs = now
                }
            }
            out.flush()
        }
    }

    companion object {
        private const val BUFFER_BYTES = 64 * 1024
        private const val POLL_MS = 200L
        private const val FLUSH_ROWS = 200
        private const val FLUSH_INTERVAL_MS = 2_000L
        private const val STOP_DRAIN_TIMEOUT_MS = 5_000L
    }
}

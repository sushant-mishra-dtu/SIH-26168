package org.idr26168.logger

import java.io.File
import java.io.OutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Zips a session folder so that the CSV files never travel apart from their `*_session.json` sidecar.
 */
object SessionExporter {

    /**
     * Zips all files in [sessionDir] into the provided [outputStream].
     * Returns the list of zipped relative file names.
     */
    fun zipSession(sessionDir: File, outputStream: OutputStream): List<String> {
        require(sessionDir.exists() && sessionDir.isDirectory) {
            "Session directory ${sessionDir.absolutePath} does not exist or is not a directory."
        }

        val files = sessionDir.listFiles()?.filter { it.isFile } ?: emptyList()
        require(files.isNotEmpty()) {
            "Session directory ${sessionDir.absolutePath} contains no files to export."
        }

        val zippedNames = mutableListOf<String>()
        ZipOutputStream(outputStream.buffered()).use { zipOut ->
            for (file in files) {
                val entry = ZipEntry(file.name)
                zipOut.putNextEntry(entry)
                file.inputStream().buffered().use { input ->
                    input.copyTo(zipOut)
                }
                zipOut.closeEntry()
                zippedNames.add(file.name)
            }
        }
        return zippedNames
    }
}

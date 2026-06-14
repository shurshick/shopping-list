package com.shoppinglist.mobile.domain.model

object VersionComparator {
    private val versionPattern = Regex("""(\d+)\.(\d+)\.(\d+)""")

    fun compare(latest: String, current: String): Int? {
        val latestVersion = parse(latest) ?: return null
        val currentVersion = parse(current) ?: return null

        for (index in latestVersion.indices) {
            val diff = latestVersion[index] - currentVersion[index]
            if (diff != 0) return diff
        }
        return 0
    }

    fun isNewer(latest: String, current: String): Boolean {
        return (compare(latest, current) ?: return false) > 0
    }

    fun parse(version: String): List<Int>? {
        val match = versionPattern.find(version.trim().removePrefix("v")) ?: return null
        return listOf(
            match.groupValues[1].toInt(),
            match.groupValues[2].toInt(),
            match.groupValues[3].toInt()
        )
    }
}

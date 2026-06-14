package com.shoppinglist.mobile.data.local

import android.content.Context

class UpdatePreferences(context: Context) {
    private val preferences = context.getSharedPreferences("shopping-list-updates", Context.MODE_PRIVATE)

    fun shouldCheck(nowMillis: Long = System.currentTimeMillis()): Boolean {
        return UpdateCheckPolicy.shouldCheck(
            lastCheckAtMillis = preferences.getLong(KEY_LAST_CHECK_AT, 0L),
            nowMillis = nowMillis
        )
    }

    fun markChecked(nowMillis: Long = System.currentTimeMillis()) {
        preferences.edit().putLong(KEY_LAST_CHECK_AT, nowMillis).apply()
    }

    fun dismissVersion(version: String) {
        preferences.edit().putString(KEY_DISMISSED_VERSION, version).apply()
    }

    fun isDismissed(version: String): Boolean {
        return UpdateCheckPolicy.isDismissed(preferences.getString(KEY_DISMISSED_VERSION, null), version)
    }

    companion object {
        private const val KEY_LAST_CHECK_AT = "lastUpdateCheckAt"
        private const val KEY_DISMISSED_VERSION = "dismissedUpdateVersion"
    }
}

object UpdateCheckPolicy {
    const val CHECK_INTERVAL_MILLIS: Long = 12L * 60L * 60L * 1000L

    fun shouldCheck(
        lastCheckAtMillis: Long,
        nowMillis: Long,
        intervalMillis: Long = CHECK_INTERVAL_MILLIS
    ): Boolean {
        return lastCheckAtMillis <= 0L || nowMillis - lastCheckAtMillis >= intervalMillis
    }

    fun isDismissed(dismissedVersion: String?, latestVersion: String): Boolean {
        return dismissedVersion == latestVersion
    }
}

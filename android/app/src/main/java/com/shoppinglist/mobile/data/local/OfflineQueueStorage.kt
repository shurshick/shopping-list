package com.shoppinglist.mobile.data.local

import android.content.Context

class OfflineQueueStorage(context: Context) {
    private val preferences = context.getSharedPreferences("shopping-list", Context.MODE_PRIVATE)

    fun loadJson(): String? = preferences.getString("pendingOperations", null)

    fun saveJson(value: String) {
        preferences.edit().putString("pendingOperations", value).apply()
    }

    fun clear() {
        preferences.edit().remove("pendingOperations").apply()
    }
}

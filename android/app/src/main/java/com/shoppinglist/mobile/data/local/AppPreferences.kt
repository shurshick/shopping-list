package com.shoppinglist.mobile.data.local

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.shoppinglist.mobile.data.ShoppingListDto

class AppPreferences(context: Context, private val gson: Gson) {
    private val preferences = context.getSharedPreferences("shopping-list", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = preferences.getString("serverUrl", "") ?: ""
        set(value) {
            preferences.edit().putString("serverUrl", value).apply()
        }

    var useTestServer: Boolean
        get() = preferences.getBoolean("useTestServer", false)
        set(value) {
            preferences.edit().putBoolean("useTestServer", value).apply()
        }

    var customServerUrl: String
        get() = preferences.getString("customServerUrl", "") ?: ""
        set(value) {
            preferences.edit().putString("customServerUrl", value).apply()
        }

    fun loadServerSettings(): ServerSettings {
        val savedCustomUrl = customServerUrl.ifBlank {
            serverUrl.takeIf { it.isNotBlank() && it != TEST_SERVER_URL }.orEmpty()
        }
        return ServerSettings(
            useTestServer = useTestServer,
            customServerUrl = savedCustomUrl
        )
    }

    fun saveServerSettings(settings: ServerSettings) {
        val normalized = settings.copy(customServerUrl = normalizeServerUrl(settings.customServerUrl))
        useTestServer = normalized.useTestServer
        customServerUrl = normalized.customServerUrl
        serverUrl = normalized.effectiveServerUrl
    }

    var themeMode: String
        get() = preferences.getString("themeMode", "system") ?: "system"
        set(value) {
            preferences.edit().putString("themeMode", value).apply()
        }

    var lastSuccessfulSync: String?
        get() = preferences.getString("lastSuccessfulSync", null)
        set(value) {
            preferences.edit().putString("lastSuccessfulSync", value).apply()
        }

    var selectedListId: Int?
        get() = preferences.getInt("selectedListId", 0).takeIf { it > 0 }
        set(value) {
            val editor = preferences.edit()
            if (value == null) {
                editor.remove("selectedListId")
            } else {
                editor.putInt("selectedListId", value)
            }
            editor.apply()
        }

    fun loadCachedLists(): List<ShoppingListDto> {
        val stored = preferences.getString("cachedLists", null) ?: return emptyList()
        return runCatching {
            val type = object : TypeToken<List<ShoppingListDto>>() {}.type
            gson.fromJson<List<ShoppingListDto>>(stored, type)
        }.getOrDefault(emptyList())
    }

    fun cacheLists(lists: List<ShoppingListDto>) {
        preferences.edit().putString("cachedLists", gson.toJson(lists)).apply()
    }

    fun clearCachedSession() {
        preferences.edit()
            .remove("cachedLists")
            .remove("lastSuccessfulSync")
            .remove("selectedListId")
            .apply()
    }

    fun nextTempId(): Int {
        val nextId = preferences.getInt("nextTempItemId", -1)
        preferences.edit().putInt("nextTempItemId", nextId - 1).apply()
        return nextId
    }
}

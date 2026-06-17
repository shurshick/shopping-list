package com.shoppinglist.mobile.data.local

const val TEST_SERVER_URL = "https://rust.bghitech.ru"

data class ServerSettings(
    val useTestServer: Boolean,
    val customServerUrl: String
) {
    val effectiveServerUrl: String
        get() = if (useTestServer) TEST_SERVER_URL else normalizeServerUrl(customServerUrl)
}

fun effectiveServerUrl(useTestServer: Boolean, customServerUrl: String): String {
    return ServerSettings(useTestServer = useTestServer, customServerUrl = customServerUrl).effectiveServerUrl
}

fun normalizeServerUrl(serverUrl: String): String {
    val trimmed = serverUrl.trim().trimEnd('/')
    if (trimmed.isBlank()) return ""
    return if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
        trimmed
    } else {
        "https://$trimmed"
    }
}


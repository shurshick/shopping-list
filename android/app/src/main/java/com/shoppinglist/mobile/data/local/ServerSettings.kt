package com.shoppinglist.mobile.data.local

const val TEST_SERVER_URL = "https://rust.bghitech.ru"

data class ServerSettings(
    val useTestServer: Boolean,
    val customServerUrl: String
) {
    val effectiveServerUrl: String
        get() = if (useTestServer) TEST_SERVER_URL else customServerUrl.trim()
}

fun effectiveServerUrl(useTestServer: Boolean, customServerUrl: String): String {
    return ServerSettings(useTestServer = useTestServer, customServerUrl = customServerUrl).effectiveServerUrl
}


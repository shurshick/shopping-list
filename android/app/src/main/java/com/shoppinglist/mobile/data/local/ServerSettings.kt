package com.shoppinglist.mobile.data.local

const val TEST_SERVER_URL = "https://rust.bghitech.ru"

fun effectiveServerUrl(useTestServer: Boolean, customServerUrl: String): String {
    return if (useTestServer) TEST_SERVER_URL else customServerUrl.trim()
}


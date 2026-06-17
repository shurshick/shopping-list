package com.shoppinglist.mobile.data.local

import org.junit.Assert.assertEquals
import org.junit.Test

class ServerSettingsTest {
    @Test
    fun effectiveServerUrlUsesTestServerWhenEnabled() {
        val settings = ServerSettings(
            useTestServer = true,
            customServerUrl = "https://my.example.com"
        )

        assertEquals(TEST_SERVER_URL, settings.effectiveServerUrl)
    }

    @Test
    fun effectiveServerUrlUsesCustomServerWhenTestModeDisabled() {
        val settings = ServerSettings(
            useTestServer = false,
            customServerUrl = "https://my.example.com"
        )

        assertEquals("https://my.example.com", settings.effectiveServerUrl)
    }

    @Test
    fun customServerIsPreservedWhenTogglingTestServer() {
        val manualSettings = ServerSettings(
            useTestServer = false,
            customServerUrl = "https://my.example.com"
        )
        val testSettings = manualSettings.copy(useTestServer = true)
        val restoredSettings = testSettings.copy(useTestServer = false)

        assertEquals(TEST_SERVER_URL, testSettings.effectiveServerUrl)
        assertEquals("https://my.example.com", restoredSettings.effectiveServerUrl)
    }
}
